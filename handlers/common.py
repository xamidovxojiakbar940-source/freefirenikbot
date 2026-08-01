"""
handlers/common.py
===================
Umumiy, "navigatsion" handlerlar: /start, /cancel, /help, /admin
va admin menyudan asosiy menyuga qaytish.

Bu router BOSHQA barcha routerlardan OLDIN ulanadi (handlers/__init__.py
ga qarang), shuning uchun bu yerdagi handlerlar foydalanuvchi qaysi
FSM holatida bo'lishidan qat'i nazar har doim ishlaydi.
"""

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import Settings
from database import Database
from keyboards import BTN_BACK, admin_menu, main_menu

logger = logging.getLogger(__name__)

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, db: Database) -> None:
    """
    /start komandasi.

    - Har doim joriy FSM holatini tozalaydi (talab #2, #25):
      bot qayta ishga tushgandan keyin yoki foydalanuvchi /start
      bossa, eski "yarim qolgan" holat hech qachon saqlanib qolmaydi.
    - Foydalanuvchini bazaga yozadi (mavjud bo'lsa, o'zgarmaydi).
    """
    await state.clear()

    await db.add_user(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name or "Noma'lum",
    )

    text = (
        f"👋 Assalomu alaykum, <b>{message.from_user.first_name}</b>!\n\n"
        "🎮 <b>Free Fire Nik Generator</b> botiga xush kelibsiz.\n\n"
        "👇 Quyidagi menyudan foydalaning."
    )
    await message.answer(text, reply_markup=main_menu())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """
    /cancel — talab #3.

    Foydalanuvchi qaysi FSM holatida bo'lishidan qat'i nazar,
    shu komandani yuborib istalgan vaqtda chiqib ketishi mumkin.
    """
    current_state = await state.get_state()

    if current_state is None:
        await message.answer("ℹ️ Hozir faol jarayon yo'q.")
        return

    await state.clear()
    await message.answer("🚫 Amal bekor qilindi.", reply_markup=main_menu())


@router.message(Command("help"))
async def cmd_help(message: Message, state: FSMContext) -> None:
    """Qisqa yordam matni."""
    await state.clear()
    text = (
        "🆘 <b>Yordam</b>\n\n"
        "🎮 Nik yaratish — ismingiz asosida stilize qilingan niklar\n"
        "🎲 Random Nik — bazadan tasodifiy nik\n"
        "📋 Tayyor Niklar — barcha tayyor niklar ro'yxati\n"
        "🔍 Nik qidirish — nik nomi bo'yicha qidiruv\n"
        "❤️ Sevimli Niklar — saqlab qo'yilgan niklaringiz\n"
        "🏆 Top Niklar — eng mashhur niklar\n\n"
        "Istalgan vaqt /cancel yuborib joriy amalni bekor qilishingiz "
        "mumkin."
    )
    await message.answer(text)


@router.message(Command("admin"))
async def cmd_admin(
    message: Message, state: FSMContext, settings: Settings
) -> None:
    """Admin panelga kirish (faqat ADMIN_IDS ro'yxatidagilar uchun)."""
    await state.clear()

    if not settings.is_admin(message.from_user.id):
        await message.answer("❌ Sizda admin panelga kirish huquqi yo'q.")
        return

    await message.answer("🔐 <b>Admin panel</b>", reply_markup=admin_menu())


@router.message(F.text == BTN_BACK)
async def back_to_main_menu(message: Message, state: FSMContext) -> None:
    """
    "⬅️ Orqaga" tugmasi — admin menyudan asosiy menyuga qaytish.

    Talab #2 ga muvofiq state har doim tozalanadi, shu bilan bog'liq
    eski FSM bugi bu nuqtada ham butunlay yo'q qilinadi.
    """
    await state.clear()
    await message.answer("🏠 Asosiy menyu", reply_markup=main_menu())
