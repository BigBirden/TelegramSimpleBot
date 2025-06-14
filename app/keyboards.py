from aiogram.types import (ReplyKeyboardMarkup, KeyboardButton, 
                           InlineKeyboardMarkup, InlineKeyboardButton)

# Клавиатура Основного функционала
main = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text='Факт'), KeyboardButton(text='Поговорка')],
                                     [KeyboardButton(text='Анекдот')],
                                     [KeyboardButton(text='Каталог')],],
                                    resize_keyboard=True,
                                    input_field_placeholder="Выберите действие...")

# Клавиатура для каталога доп. функций
catalog = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='Рандомизатор', callback_data='rand')]])

# Создаем клавиатуру с кнопкой "Еще раз" для рандомизации
again = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Еще раз", callback_data="repeat_random")]
    ]
)

# Клава для VKID
def get_auth_keyboard(auth_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚪 Войти через VK", url=auth_url)]
    ])