"""
keyboards.py
============
Barcha Reply va Inline klaviaturalar shu yerda.

MUHIM ARXITEKTURA QARORI:
    Har bir menyu tugmasining matni pastda konstanta sifatida
    e'lon qilingan va `ALL_MENU_TEXTS` to'plamiga yig'ilgan.

    Nima uchun bu FSM buzilishining oldini oladi:
    FSM qadam handlerlari (masalan "yangi nikni yuboring" kutayotgan
    handler) shu to'plamdan foydalanib, "agar foydalanuvchi matn
    o'rniga biror menyu tugmasini bossa — buni kiritilgan qiymat
    deb qabul qilmaymiz" degan qoidani qo'llaydi
    (handlers/admin.py va handlers/user.py fayllariga qarang).
"""

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

# ---------------------------------------------------------------------- #
# Foydalanuvchi menyusi tugmalari
# ---------------------------------------------------------------------- #

BTN_CREATE_NICK = "🎮 Nik yaratish"
BTN_RANDOM_NICK = "🎲 Random Nik"
BTN_READY_NICKS = "📋 Tayyor Niklar"
BTN_SEARCH_NICK = "🔍 Nik qidirish"
BTN_FAVORITES = "❤️ Sevimli Niklar"
BTN_TOP_NICKS = "🏆 Top Niklar"
BTN_INVISIBLE = "✨ Ko'rinmas belgi"
BTN_BACK = "⬅️ Orqaga"

USER_MENU_TEXTS = frozenset(
    {
        BTN_CREATE_NICK,
        BTN_RANDOM_NICK,
        BTN_READY_NICKS,
        BTN_SEARCH_NICK,
        BTN_FAVORITES,
        BTN_TOP_NICKS,
        BTN_INVISIBLE,
    }
)

# ---------------------------------------------------------------------- #
# Admin menyusi tugmalari
# ---------------------------------------------------------------------- #

BTN_STATS = "📊 Statistika"
BTN_BROADCAST = "📢 Broadcast"
BTN_ADD_NICK = "➕ Nik qo'shish"
BTN_DELETE_NICK = "❌ Nik o'chirish"
BTN_USERS_COUNT = "👥 Foydalanuvchilar soni"
BTN_BACKUP = "💾 Backup"

ADMIN_MENU_TEXTS = frozenset(
    {
        BTN_STATS,
        BTN_BROADCAST,
        BTN_ADD_NICK,
        BTN_DELETE_NICK,
        BTN_USERS_COUNT,
        BTN_BACKUP,
        BTN_BACK,
    }
)

# Har qanday FSM qadam handleri shu to'plamni tekshirib, foydalanuvchi
# aslida menyuga qaytmoqchi ekanini aniqlay oladi.
ALL_MENU_TEXTS = USER_MENU_TEXTS | ADMIN_MENU_TEXTS | {BTN_BACK}


# ---------------------------------------------------------------------- #
# Reply klaviaturalar
# ---------------------------------------------------------------------- #

def main_menu() -> ReplyKeyboardMarkup:
    """Oddiy foydalanuvchi uchun asosiy menyu."""
    keyboard = [
        [KeyboardButton(text=BTN_CREATE_NICK)],
        [KeyboardButton(text=BTN_RANDOM_NICK), KeyboardButton(text=BTN_READY_NICKS)],
        [KeyboardButton(text=BTN_SEARCH_NICK), KeyboardButton(text=BTN_FAVORITES)],
        [KeyboardButton(text=BTN_TOP_NICKS), KeyboardButton(text=BTN_INVISIBLE)],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def admin_menu() -> ReplyKeyboardMarkup:
    """Admin panel klaviaturasi."""
    keyboard = [
        [KeyboardButton(text=BTN_STATS), KeyboardButton(text=BTN_USERS_COUNT)],
        [KeyboardButton(text=BTN_ADD_NICK), KeyboardButton(text=BTN_DELETE_NICK)],
        [KeyboardButton(text=BTN_BROADCAST), KeyboardButton(text=BTN_BACKUP)],
        [KeyboardButton(text=BTN_BACK)],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


# ---------------------------------------------------------------------- #
# Inline klaviaturalar
# ---------------------------------------------------------------------- #

def _truncate_to_bytes(text: str, max_bytes: int) -> str:
    """
    Telegram `callback_data` MAKSIMAL 64 baytni qabul qiladi (belgi
    emas, bayt!). Free Fire niklarida ko'p uchraydigan maxsus Unicode
    belgilar (masalan "亗", "꧁") UTF-8'da 3 baytgacha egallashi
    mumkin, shuning uchun oddiy `text[:N]` yetarli emas — bu funksiya
    satrni bayt chegarasidan oshirmay, belgini yarmidan uzib
    qo'ymaydigan qilib qisqartiradi.
    """
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def favorite_button(nick_text: str) -> InlineKeyboardMarkup:
    """Ko'rsatilgan nik ostiga "sevimlilarga qo'shish" tugmasi."""
    # "fav_add:" prefiksi 8 bayt, callback_data limiti 64 bayt —
    # shuning uchun nik matni 56 baytdan oshmasligi kerak.
    safe_nick = _truncate_to_bytes(nick_text, 56)
    button = InlineKeyboardButton(
        text="❤️ Sevimlilarga qo'shish",
        callback_data=f"fav_add:{safe_nick}",
    )
    return InlineKeyboardMarkup(inline_keyboard=[[button]])


def favorites_list_keyboard(favorites) -> InlineKeyboardMarkup:
    """Har bir sevimli nik uchun o'chirish tugmasi bilan ro'yxat."""
    rows = [
        [
            InlineKeyboardButton(
                text=f"🗑 {row['nick_text']}",
                callback_data=f"fav_del:{row['id']}",
            )
        ]
        for row in favorites
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pagination_keyboard(page: int, total_pages: int) -> InlineKeyboardMarkup:
    """"Tayyor Niklar" ro'yxati uchun sahifalash tugmalari."""
    buttons = []

    if page > 0:
        buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"nicks_page:{page - 1}")
        )

    buttons.append(
        InlineKeyboardButton(
            text=f"{page + 1}/{total_pages}", callback_data="noop"
        )
    )

    if page < total_pages - 1:
        buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"nicks_page:{page + 1}")
        )

    return InlineKeyboardMarkup(inline_keyboard=[buttons])


def cancel_inline_keyboard() -> InlineKeyboardMarkup:
    """FSM qadamlarida "Bekor qilish" tugmasi (reply /cancel bilan bir qatorda)."""
    button = InlineKeyboardButton(text="🚫 Bekor qilish", callback_data="cancel_fsm")
    return InlineKeyboardMarkup(inline_keyboard=[[button]])
