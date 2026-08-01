from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def menu():

    keyboard = [

        [KeyboardButton(text="🎮 Nik yaratish")],

        [KeyboardButton(text="🎲 Random Nik"),
         KeyboardButton(text="✨ Ko'rinmas belgi")],

        [KeyboardButton(text="📋 Tayyor Niklar")]

    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )


def admin_menu():

    keyboard = [

        [KeyboardButton(text="📊 Statistika")],

        [KeyboardButton(text="📢 Reklama")],

        [KeyboardButton(text="➕ Nik qo'shish")],

        [KeyboardButton(text="❌ Nik o'chirish")],

        [KeyboardButton(text="⬅️ Orqaga")]

    ]

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )