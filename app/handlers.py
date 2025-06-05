from aiogram import types, F, Router                    # Непосредственно создание ботов
from aiogram.filters import Command, CommandStart       # Фильтр для обработки команд
from aiogram.types import CallbackQuery
import random                                           # Для поговорок и фактов
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import asyncio                                          # Позволяет выполнять код асинхронно (параллельно)

from .func import load_data, load_jokes, randomizing       # Функции загрузки данных и рандомизации
from . import keyboards as kb                              # Reply-Клавиатуры и Inline-клавиатуры

facts = load_data('data/facts.txt')                 # Загрузка данных
thinks = load_data('data/thinks.txt')
jokes = load_jokes('data/jokes.txt')

class Randomizer(StatesGroup):                      # Класс для состояний
    min = State()
    max = State()
    
router = Router()                                   # Объявляем роутер, который будет диспетчером

# Обработчик команды /start
@router.message(CommandStart())
async def send_welcome(message: types.Message):
    await message.reply("""Привет!\nЯ простейший бот-говорилка, по твоему выбору я могу тебе отправить интересный факт, поговорку или анекдот.\n\nВведи /help для просмотра списка команд.""", reply_markup=kb.main)

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
    

# Обработчик команды /help
@router.message(Command('help'))
async def send_help(message: types.Message):
    help_text = """
    Доступные команды:
    /start - Начать работу
    /help - Список команд
    
    Нажми кнопку:
        "Факт" — для получения интересного факта
        "Поговорка" — для получения мудрой цитаты
        "Анекдот" — для получения (не)смешной шутки
        "Каталог" — выводит меню с дополнительными функциями
    """
    await message.answer(help_text)
    
# Секретные функции
    
# Запуск рандомизации
@router.callback_query(F.data == 'rand')
async def randF(callback: CallbackQuery, state: FSMContext):
    await callback.answer('Вы выбрали категорию "Рандомизатор"')
    
    await state.set_state(Randomizer.min)
    await callback.message.answer('Введите наименьшее число для диапазона') # type: ignore
    
# Обработчик состояния min
@router.message(Randomizer.min)
async def get_min(message: types.Message, state: FSMContext):
    await state.update_data(min=message.text)
    await state.set_state(Randomizer.max)
    await message.answer('Введите наибольшее число для диапазона')
    
# Обработчик состояния max
@router.message(Randomizer.max)
async def get_max(message: types.Message, state: FSMContext):
    await state.update_data(max=message.text)
    data = await state.get_data()
    await message.answer(f'Диапазон чисел: [{data["min"]} .. {data["max"]}]')
    
    if data["max"] <= data["min"]:
        await message.answer("Максимальное число должно быть больше минимального!")
        return
    
    # Получаем результаты рандомизации
    eliminated, winner = randomizing(int(data["min"]), int(data["max"]))
    # Выводим процесс выбывания чисел
    for num in eliminated:
        await message.answer(f"Выбыло число: {num}")
        # Можно добавить небольшую паузу для эффекта
        await asyncio.sleep(0.5)
    
    # Объявляем победителя
    await message.answer(f"Победитель: {winner}", reply_markup=kb.again)
    await state.clear()
    
# Перезапуск рандомизации
@router.callback_query(F.data == "repeat_random")
async def repeat_randomization(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(Randomizer.min)
    await callback.message.answer('Введите наименьшее число для диапазона') # type: ignore
    