import secrets
from aiogram import types, F, Router                    # Непосредственно создание ботов
from aiogram.filters import Command, CommandStart       # Фильтр для обработки команд
from aiogram.types import CallbackQuery, FSInputFile
import random                                           # Для поговорок и фактов
from aiogram.fsm.state import State, StatesGroup        # Импорт состояний для рандомизатора
from aiogram.fsm.context import FSMContext
import asyncio                                          # Позволяет выполнять код асинхронно (параллельно)
import os
from urllib.parse import quote                          # Для vk_auth
import redis                                            # Для передачи state и code_challenge

from sqlalchemy import text

from func import load_data, load_jokes, randomizing, validate_number,  generate_pkce_pair      # Функции загрузки данных и рандомизации
import keyboards as kb                                                     # Reply-Клавиатуры и Inline-клавиатуры
from db import get_session
from middlewares import MessageSaverMiddleware

# Подключение к Redis
redis_client = redis.Redis(
    host="redis",               # Имя сервиса в docker-compose
    port=6379,
    db=0,
    decode_responses=True       # Чтобы получать строки вместо bytes
)

facts = load_data('data/facts.txt')                 # Загрузка данных
thinks = load_data('data/thinks.txt')
jokes = load_jokes('data/jokes.txt')

class Randomizer(StatesGroup):                      # Класс для состояний
    min = State()
    max = State()
    
router = Router()                                   # Объявляем роутер, который будет диспетчером
router.message.middleware(MessageSaverMiddleware())

# Обработчик команды /start
@router.message(CommandStart())
async def send_welcome(message: types.Message):
    # Отправляем приветственное сообщение
    await message.reply(
        """Привет!\nЯ простейший бот-говорилка, по твоему выбору я могу тебе отправить интересный факт, поговорку или анекдот.\n\nВведи /help для просмотра списка команд.""",
        reply_markup=kb.main
    )

# Обработчик команды /help
@router.message(Command('help'))
async def send_help(message: types.Message):
    help_text = """
    Доступные команды:
    /start - Начать работу
    /help - Список команд
    /base - Проверить подключение к базе данных
    /pray - Помолиться за здравие
    
    Нажми кнопку:
        "Факт" — для получения интересного факта
        "Поговорка" — для получения мудрой цитаты
        "Анекдот" — для получения (не)смешной шутки
        "Каталог" — выводит меню с дополнительными функциями
    """
    await message.answer(help_text)

# Обработчик команды /base
@router.message(Command('base'))
async def dbcheck(message: types.Message):
    try:
        async with get_session() as session:
            await session.execute(text("SELECT 1"))
            # Если подключение успешно, выполняем дальнейшие операции
            await message.answer("Успешное подключение к базе данных")
            
    except Exception as e:
        # Если возникла ошибка подключения
        await message.answer(f"Ошибка подключения к базе данных: {str(e)}")

# Обработчик команды /pray (Молитва)
@router.message(Command('pray'))
async def pray(message: types.Message):
    phrases = [                                                     # Список возможных фраз
        "Господь услышал ваши молитвы.",
        "Вы поставили свечку в церкви.",
        "Священник в восторге."
    ]
    photos = [
        "picts/church.jpg",
        "picts/church1.jpg",
        "picts/church2.jpg"
    ]
    random_phrase = random.choice(phrases)                      # Выбираем случайную фразу
    random_number = random.randint(1, 100)                      # Генерируем случайное число от 1 до 100
    photo_path = random.choice(photos)                          # Выбираем фото
    captionL = (
        f"{random_phrase}\n\n"
        f"Ваш навык 'Религия' повышен на: {random_number}!"
    )
    await message.answer_photo(FSInputFile(photo_path), 
                               caption=captionL)

# Получение id пользователя
@router.message(Command('myid'))
async def show_my_id(message: types.Message):
    if message.from_user:
        user_id = message.from_user.id
        await message.answer(f"Ваш Telegram ID: {user_id}")
        
    else:
        raise Exception("Ошибка при получении ID")

# Получение id чата
@router.message(Command('chatid'))
async def get_chat_id(message: types.Message):
    chat_id = message.chat.id
    await message.answer(f"ID этого чата: {chat_id}")
    
# Получение id сообщения
@router.message(Command('msgid'))
async def get_message_id(message: types.Message):
    msg_id = message.message_id
    await message.answer(f"ID этого сообщения: {msg_id}")

# Обработчик команды /users (Вывод всех пользователей в БД)
@router.message(Command('users'))
async def list_users(message: types.Message):
    try:
        async with get_session() as session:
            result = await session.execute(text("SELECT telegram_id, username FROM users"))
            users = result.fetchall()
            if not users:
                await message.answer("Пользователей в базе нет.")
                return
            reply = "Пользователи:\n"
            for user in users:
                reply += f"ID: {user[0]}, Имя: {user[1]}\n"
            await message.answer(reply)
    except Exception as e:
        await message.answer(f"Ошибка при получении пользователей: {str(e)}")

# Обработчик команды /re_chat
@router.message(Command('re_chat'))
async def re_chat(message: types.Message):
    try:
        if message.from_user:
            user_id = message.from_user.id 
        else:
            raise Exception("message.from_user пуст!")
    except ValueError:
        await message.answer("ID должен быть числом.")
        return
    except Exception:
        await message.answer("Сообщение пусто.")
        return

    try:
        async with get_session() as session:
            result = await session.execute(
                text(
                    "SELECT m.text, m.created_at FROM messages m "
                    "JOIN dialogs d ON m.dialog_id = d.id "
                    "WHERE d.user_id = :uid "
                    "ORDER BY m.created_at DESC"
                ),
                {'uid': user_id}
            )
            messages = result.fetchall()
            if not messages:
                await message.answer("У этого пользователя сообщений нет.")
                return
            for text_msg, created in messages:
                dt_str = created.strftime("%d.%m.%Y %H:%M")
                await message.answer(f"🕒 {dt_str}\n📝 {text_msg}")
    except Exception as e:
        await message.answer(f"Ошибка: {str(e)}")

# Обработчик команды /vk_auth
@router.message(Command("vk_auth"))
async def send_vk_auth_link(message: types.Message):
    client_id = os.getenv("VK_APP_ID")                              # ID вашего Standalone-приложения
    redirect_uri = os.getenv("VK_CALLBACK_URL")                     # URL для callback
    scope = "email phone"                                # Запрашиваемые права
    
    if not client_id:
        await message.answer("Ошибка: не настроен VK_APP_ID")
        return
    if not redirect_uri:
        await message.answer("Ошибка: не настроен VK_CALLBACK_URL")
        return
    
    state = secrets.token_urlsafe(16)                               # Создаем 
    code_verifier, code_challenge = generate_pkce_pair()
    
    redis_key = f"vk_auth:{state}"
    redis_client.hset(
        redis_key,                                                  # Сохраняем в Redis (ключ: "vk_auth:{state}")
        mapping={
            "code_verifier": code_verifier,
            "telegram_id": str(message.from_user.id) # type: ignore
        }
    )
    redis_client.expire(redis_key, 600)  # Удалить через 10 минут
    
    auth_url = (
        f"https://id.vk.com/authorize?"
        f"response_type=code&"
        f"client_id={client_id}&"
        f"redirect_uri={quote(redirect_uri)}&"
        f"scope={quote(scope)}&"
        f"code_challenge={code_challenge}&"
        f"code_challenge_method=S256&"
        f"state={state}"
    )
    
    
    # Отправляем сообщение с ссылкой
    await message.answer(
        "<b>🔐 Авторизация VK</b>\n\n"
        "Вы можете авторизоваться через VK!\n"
        "Нажмите кнопку ниже чтобы продолжить:",
        parse_mode="HTML",
        reply_markup=kb.get_auth_keyboard(auth_url)
    )

# Вывод фактов
@router.message(F.text.lower() == "факт")
async def fact(message: types.Message):
    if facts:  # Проверяем, что список не пустой
        await message.answer("Факт №" + random.choice(facts))
    else:
        await message.answer("Факты кончились...")
    

# Вывод поговорок
@router.message(F.text.lower() == "поговорка")
async def think(message: types.Message):
    if thinks:  # Проверяем, что список не пустой
        await message.answer("Поговорка №" + random.choice(thinks))
    else:
        await message.answer("Поговорки кончились...")
    
# Вывод анекдотов
@router.message(F.text.lower() == "анекдот")
async def joke(message: types.Message):
    if jokes:  # Проверяем, что список не пустой
        await message.answer(random.choice(jokes))
    else:
        await message.answer("Шутки кончились...")
        
# Каталог всяких плюшек
@router.message(F.text.lower() ==  'каталог')
async def catalog(message: types.Message):
    await message.answer('Выберите категорию говорилки', reply_markup=kb.catalog)
    
# Запуск рандомизации
@router.callback_query(F.data == 'rand')
async def randF(callback: CallbackQuery, state: FSMContext):
    await callback.answer('Вы выбрали категорию "Рандомизатор"')
    
    await state.set_state(Randomizer.min)
    await callback.message.answer('Введите наименьшее число для диапазона') # type: ignore
    
# Обработчик состояния min
@router.message(Randomizer.min)
async def get_min(message: types.Message, state: FSMContext):
    if message.text is None:
        await message.answer("Пожалуйста, введите число, а не файл или стикер!")
        return
    
    min_num = validate_number(message.text)
    if min_num is None:
        await message.answer("Пожалуйста, введите целое положительное число!")
        return
    
    await state.update_data(min=min_num)
    await state.set_state(Randomizer.max)
    await message.answer('Введите наибольшее число для диапазона')
    
# Обработчик состояния max
@router.message(Randomizer.max)
async def get_max(message: types.Message, state: FSMContext):
    if message.text is None:
        await message.answer("Пожалуйста, введите число, а не файл или стикер!")
        return
    
    max_num = validate_number(message.text)
    if max_num is None:
        await message.answer("Пожалуйста, введите целое положительное число!")
        return
    
    data = await state.get_data()
    min_num = data["min"]
    
    if max_num <= min_num:
        await message.answer("Максимальное число должно быть больше минимального!")
        return
    
    try:
        eliminated, winner = randomizing(min_num, max_num)
        
        await message.answer(f"Диапазон чисел: [{min_num}...{max_num}]")
        for num in eliminated:
            await message.answer(f"Выбыло число: {num}")
            await asyncio.sleep(0.5)
        
        await message.answer(f"Победитель: {winner}", reply_markup=kb.again)
    
    except ValueError as e:
        await message.answer(f"Ошибка: {str(e)}")
    except Exception:
        await message.answer("Произошла ошибка при рандомизации. Попробуйте задать другой диапазон.")
    finally:
        await state.clear()
    
# Перезапуск рандомизации
@router.callback_query(F.data == "repeat_random")
async def repeat_randomization(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Randomizer.min)
    await callback.message.answer('Введите наименьшее число для диапазона') # type: ignore
    
# Секретные функции
# Сбэу комар, который ведет на бота моего одногруппника
@router.message(lambda message: message.text.lower() in {'сбеу', 'сбэу', 'sbey', 'sbeu'})
async def sbeu(message: types.Message):
    photo_path = "picts/komar.jpg"
    bot_username = "obdolbos_bot"
    captionL = (
        "Уже в пути к тебе\.\.\."
        f"\n\n[Или иди навстречу\.](https://t.me/{bot_username})"
    )
    await message.answer_photo(FSInputFile(photo_path), 
                               caption=captionL,
                               parse_mode="MarkdownV2")
    
# Игра в пинг-понг
@router.message(F.text.lower().in_(["ping", "пинг"]))
async def pong(message: types.Message):
    await message.answer('pong')
    
# Рыбко
@router.message(F.text.lower().in_(["fihs", "fish"]))
async def fish(message: types.Message):
    gif_path = "picts/fish.gif"
    await message.answer_animation(FSInputFile(gif_path))
    
# Поддержка в тяжелой ситуации
@router.message(F.text.contains("помогите"))
async def luck(message: types.Message):
    photo_path = "picts/cat.jpg"
    captionL = (
        "Все будет хорошо. Бог поможет..."
    )
    await message.answer_photo(FSInputFile(photo_path), 
                               caption=captionL)
    
@router.message(F.text)
async def handle_all_text_messages(message: types.Message):
    # Тут ваш код, например, вызов middleware или логика
    pass