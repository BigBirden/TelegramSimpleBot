import logging                                  # Модуль для логирования (ведения журнала событий)
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv                  # Загружает переменные окружения (в данном случае токен бота)
import os                                       # Позволяет работать с переменными окружения
import asyncio                                  # Позволяет выполнять код асинхронно (параллельно)
from sqlalchemy import create_engine            # Подключение к БД (пустой)

from handlers import router

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="base", description="Проверка БД"),
        BotCommand(command="pray", description="Молитва")
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

# Запуск бота
async def main():
    DATABASE_URL = "postgresql://postgres:postgres@db:5432/postgres"            # Подключение к PostgreSQL (URL из docker-compose)
    engine = create_engine(DATABASE_URL)
    
    load_dotenv()                       # Получает все переменные из файла .env
    TOKEN = os.getenv("BOT_TOKEN")      # Получаем нужную переменную
    if TOKEN is None:       
        raise ValueError("Не найден BOT_TOKEN в переменных окружения или .env файле")       # Нужно, чтобы токен точно был строкой

    logging.basicConfig(level=logging.INFO)     # Настройка логов
    logger = logging.getLogger(__name__)
    
    with engine.connect() as conn:                                              # Просто проверяем подключение
        logger.info("Бот подключился к PostgreSQL!")
    logger.info("Запуск бота...")
    
    bot = Bot(token=TOKEN)          # Создание самого бота
    dp = Dispatcher()               # Создание диспетчера обработки сообщений
    
    # Передаём engine в хендлеры (чтобы они создавали новые подключения при запросах)
    dp["engine"] = engine
    
    await set_commands(bot)  # Установка меню команд
    dp.include_router(router)       # Включаем роутер
    try:
        await dp.start_polling(bot)     # Бесконечно слушает сервера Телеграмма, чтобы отреагировать на сообщения
    finally:
        engine.dispose()  # Закрываем все соединения при остановке бота


if __name__ == '__main__':          # Запускается только в том случае, если данный файл запускаетс непосредственно
    try:
        asyncio.run(main())         # Производит асинхронный запуск
    except KeyboardInterrupt:
        print("Бот выключен")