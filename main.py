import logging                                  # Модуль для логирования (ведения журнала событий)
from aiogram.types import BotCommand, BotCommandScopeDefault
from aiogram import Bot, Dispatcher
from dotenv import load_dotenv                  # Загружает переменные окружения (в данном случае токен бота)
import os                                       # Позволяет работать с переменными окружения
import asyncio                                  # Позволяет выполнять код асинхронно (параллельно)

from app.handlers import router

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="help", description="Помощь")
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())

# Запуск бота
async def main():
    load_dotenv()                       # Получает все переменные из файла .env
    TOKEN = os.getenv("BOT_TOKEN")      # Получаем нужную переменную
    if TOKEN is None:       
        raise ValueError("Не найден BOT_TOKEN в переменных окружения или .env файле")       # Нужно, чтобы токен точно был строкой

    logging.basicConfig(level=logging.INFO)     # Настройка логов
    
    
    bot = Bot(token=TOKEN)          # Создание самого бота
    dp = Dispatcher()               # Создание диспетчера обработки сообщений
    
    await set_commands(bot)  # Установка меню команд
    dp.include_router(router)       # Включаем роутер
    await dp.start_polling(bot)     # Бесконечно слушает сервера Телеграмма, чтобы отреагировать на сообщения


if __name__ == '__main__':          # Запускается только в том случае, если данный файл запускаетс непосредственно
    try:
        asyncio.run(main())         # Производит асинхронный запуск
    except KeyboardInterrupt:
        print("Бот выключен")