import sys
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv                  # Загружает переменные окружения (в данном случае токен бота)
import os                                       # Позволяет работать с переменными окружения
import asyncio                                  # Позволяет выполнять код асинхронно (параллельно)
from sqlalchemy.ext.asyncio import create_async_engine            # Подключение к БД (пустой)
from sqlalchemy import text  # Добавьте этот импорт

from logger import logger
from handlers import router
from db import init_db, get_session, engine

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
    
    load_dotenv()                                               # Получает все переменные из файла .env
    DATABASE_URL = os.getenv("DATABASE_URL")                   # Подключение к PostgreSQL (URL из docker-compose)
    logger.info(f"Используемый DATABASE_URL: {DATABASE_URL}")  # Должен начинаться с postgresql+asyncpg://
    if DATABASE_URL is None:       
        raise ValueError("Не найден DATABASE_URL в переменных окружения или .env файле")       # Нужно, чтобы URL точно был строкой
    init_db(DATABASE_URL)  # Инициализируем engine
    
    TOKEN = os.getenv("BOT_TOKEN")      # Получаем нужную переменную
    if TOKEN is None:       
        raise ValueError("Не найден BOT_TOKEN в переменных окружения или .env файле")       # Нужно, чтобы токен точно был строкой
    
    # Проверка подключения к БД
    try:
        async with get_session() as session:
            await session.execute(text("SELECT 1"))  # Асинхронная проверка
            logger.info("Успешное подключение к PostgreSQL!")
    except Exception as e:
        logger.error(f"Ошибка подключения к БД: {e}")
        raise
    
    bot = Bot(token=TOKEN)          # Создание самого бота
    dp = Dispatcher()               # Создание диспетчера обработки сообщений
    
    await set_commands(bot)  # Установка меню команд
    dp.include_router(router)       # Включаем роутер
    try:
        await dp.start_polling(bot)     # Бесконечно слушает сервера Телеграмма, чтобы отреагировать на сообщения
    finally:
        if engine:
            await engine.dispose()  # Асинхронное закрытие соединений
        logger.info("Бот остановлен, соединения закрыты")


if __name__ == '__main__':          # Запускается только в том случае, если данный файл запускаетс непосредственно
    try:
        asyncio.run(main())         # Производит асинхронный запуск
    except KeyboardInterrupt:
        print("Бот выключен")