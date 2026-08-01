from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import random
import aiosqlite

from config import ADMIN_ID
from keyboards import menu, admin_menu
from database import *

router = Router()


class AdminState(StatesGroup):
    reklama = State()
    addnick = State()
    delnick = State()


DEFAULT_NICKS = [
    "亗 XAMIDOV 亗",
    "꧁༒LEGEND༒꧂",
    "★SNIPER★",
    "☠DARK☠",
    "♛KING♛",
    "⚡PRO⚡",
    "メDEVILメ",
    "ツGHOSTツ",
]


@router.message(Command("start"))
async def start(message: Message):

    await add_user(
        message.from_user.id,
        message.from_user.full_name
    )

    text = f"""
👋 Assalomu alaykum <b>{message.from_user.first_name}</b>

🎮 Free Fire Nick Generator botiga xush kelibsiz.

👇 Quyidagi menyudan foydalaning.
"""

    await message.answer(
        text,
        reply_markup=menu()
    )


@router.message(Command("admin"))
async def admin(message: Message):

    if message.from_user.id != ADMIN_ID:
        return await message.answer("❌ Siz admin emassiz.")

    await message.answer(
        "🔐 Admin Panel",
        reply_markup=admin_menu()
    )


@router.message(lambda m: m.text == "📊 Statistika")
async def statistics(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    users = await get_users_count()

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            "SELECT COUNT(*) FROM nicks"
        )

        nick_count = (await cursor.fetchone())[0]

    await message.answer(
        f"""
📊 BOT STATISTIKASI

👥 Foydalanuvchilar: {users}

🎮 Niklar: {nick_count}
"""
    )
# ==========================
# 📢 REKLAMA
# ==========================

@router.message(lambda m: m.text == "📢 Reklama")
async def reklama(message: Message, state: FSMContext):

    if message.from_user.id != ADMIN_ID:
        return

    await message.answer(
        "📨 Hammaga yuboriladigan xabarni yuboring."
    )

    await state.set_state(AdminState.reklama)


@router.message(AdminState.reklama)
async def send_reklama(message: Message, state: FSMContext, bot):

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            "SELECT user_id FROM users"
        )

        users = await cursor.fetchall()

    success = 0

    for user in users:

        try:

            await bot.send_message(
                user[0],
                message.text
            )

            success += 1

        except:
            pass

    await message.answer(
        f"✅ Reklama {success} ta foydalanuvchiga yuborildi."
    )

    await state.clear()


# ==========================
# ➕ NIK QO'SHISH
# ==========================

@router.message(lambda m: m.text == "➕ Nik qo'shish")
async def addnick(message: Message, state: FSMContext):

    if message.from_user.id != ADMIN_ID:
        return

    await message.answer(
        "➕ Yangi nikni yuboring."
    )

    await state.set_state(AdminState.addnick)


@router.message(AdminState.addnick)
async def save_nick(message: Message, state: FSMContext):

    await add_nick(message.text)

    await message.answer(
        "✅ Nik bazaga qo'shildi."
    )

    await state.clear()


# ==========================
# ❌ NIK O'CHIRISH
# ==========================

@router.message(lambda m: m.text == "❌ Nik o'chirish")
async def delnick(message: Message, state: FSMContext):

    if message.from_user.id != ADMIN_ID:
        return

    await message.answer(
        "❌ O'chiriladigan nikni yuboring."
    )

    await state.set_state(AdminState.delnick)


@router.message(AdminState.delnick)
async def remove_nick(message: Message, state: FSMContext):

    await delete_nick(message.text)

    await message.answer(
        "✅ Nik o'chirildi."
    )

    await state.clear()
# ==========================
# 🎮 NIK YARATISH
# ==========================

@router.message(lambda m: m.text == "🎮 Nik yaratish")
async def nick_info(message: Message):
    await message.answer(
        "📝 Ismingizni yuboring.\n\nMasalan: Shoxruz"
    )


@router.message(lambda m: m.text and not m.text.startswith("/") and m.text not in [
    "🎮 Nik yaratish",
    "🎲 Random Nik",
    "📋 Tayyor Niklar",
    "✨ Ko'rinmas belgi",
    "📊 Statistika",
    "📢 Reklama",
    "➕ Nik qo'shish",
    "❌ Nik o'chirish",
    "⬅️ Orqaga"
])
async def generate_nick(message: Message):

    name = message.text.strip()

    nicks = [
        f"亗{name}亗",
        f"꧁{name}꧂",
        f"『{name}』",
        f"★{name}★",
        f"⚡{name}⚡",
        f"♛{name}♛",
        f"メ{name}メ",
        f"☠{name}☠",
        f"{name}ㅤFF",
        f"{name}ㅤPRO",
        f"乂{name}乂",
        f"ツ{name}ツ",
        f"꧁༒{name}༒꧂",
        f"{name}〆",
        f"Xx{name}xX",
    ]

    text = "🎮 <b>Siz uchun niklar:</b>\n\n"

    for nick in nicks:
        text += f"• <code>{nick}</code>\n"

    await message.answer(text)


# ==========================
# 🎲 RANDOM NIK
# ==========================

@router.message(lambda m: m.text == "🎲 Random Nik")
async def random_nick(message: Message):

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT nick FROM nicks")
        data = await cursor.fetchall()

    if data:
        nick = random.choice(data)[0]
    else:
        nick = random.choice(DEFAULT_NICKS)

    await message.answer(
        f"🎲 Tasodifiy nik:\n\n<code>{nick}</code>"
    )


# ==========================
# 📋 TAYYOR NIKLAR
# ==========================

@router.message(lambda m: m.text == "📋 Tayyor Niklar")
async def ready_nicks(message: Message):

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("SELECT nick FROM nicks LIMIT 30")
        data = await cursor.fetchall()

    if data:
        text = ""
        for nick in data:
            text += f"• <code>{nick[0]}</code>\n"
    else:
        text = "\n".join(DEFAULT_NICKS)

    await message.answer(
        "📋 <b>Tayyor Niklar</b>\n\n" + text
    )


# ==========================
# ✨ KO'RINMAS BELGI
# ==========================

@router.message(lambda m: m.text == "✨ Ko'rinmas belgi")
async def invisible(message: Message):

    await message.answer(
        "👇 Nusxalang:\n\n<code>ㅤ</code>\n\nBu Free Fire uchun ko'rinmas belgidir."
    )


# ==========================
# ⬅️ ORQAGA
# ==========================

@router.message(lambda m: m.text == "⬅️ Orqaga")
async def back(message: Message):

    await message.answer(
        "🏠 Asosiy menyu",
        reply_markup=menu()
    )
