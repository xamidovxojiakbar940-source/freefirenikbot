"""
handlers/user.py
=================
Oddiy foydalanuvchi funksiyalari: nik generatsiya, random nik,
tayyor niklar (sahifalab), qidiruv, sevimlilar, top niklar.

Bu router `handlers/__init__.py` da ENG OXIRIDA ulanadi, chunki u
"erkin matn" qabul qiladigan eng keng filtrlarni o'z ichiga oladi
(masalan `generate_nick` — istalgan matnga javob beradi). Agar bu
router oldinroq turganida, u admin/umumiy tugmalarni "yutib" olishi
mumkin edi — aynan shu turdagi xato eski loyihaning asosiy muammosi
edi.
"""

import logging
import random

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import Database
from keyboards import (
    ALL_MENU_TEXTS,
    BTN_CREATE_NICK,
    BTN_FAVORITES,
    BTN_INVISIBLE,
    BTN_RANDOM_NICK,
    BTN_READY_NICKS,
    BTN_SEARCH_NICK,
    BTN_TOP_NICKS,
    favorite_button,
    favorites_list_keyboard,
    pagination_keyboard,
)
from states import UserStates

logger = logging.getLogger(__name__)

router = Router(name="user")

# Bazada hech qanday nik bo'lmagan taqdirda ishlatiladigan zaxira ro'yxat.
DEFAULT_NICKS = (
    "亗 LEGEND 亗",
    "꧁༒KING༒꧂",
    "★SNIPER★",
    "☠DARK☠",
    "♛ROYAL♛",
    "⚡PRO⚡",
    "メGHOSTメ",
    "ツDEVILツ",
)

NICK_TEMPLATES = (
    "亗{name}亗",
    "꧁{name}꧂",
    "『{name}』",
    "★{name}★",
    "⚡{name}⚡",
    "♛{name}♛",
    "メ{name}メ",
    "☠{name}☠",
    "{name}ㅤFF",
    "{name}ㅤPRO",
    "乂{name}乂",
    "ツ{name}ツ",
    "꧁༒{name}༒꧂",
    "{name}〆",
    "Xx{name}xX",
)


def _not_menu_text(message: Message) -> bool:
    """FSM kutish handlerlari uchun himoya filtri (admin.py dagi bilan bir xil)."""
    return bool(message.text) and message.text not in ALL_MENU_TEXTS


# ------------------------------------------------------------------ #
# 🎮 Nik yaratish (ism asosida)
# ------------------------------------------------------------------ #

@router.message(F.text == BTN_CREATE_NICK)
async def create_nick_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(UserStates.waiting_name_for_nick)
    await message.answer(
        "📝 Ismingizni yuboring.\n\nMasalan: <i>Shoxruz</i>\n\n"
        "Bekor qilish uchun /cancel yozing."
    )


@router.message(UserStates.waiting_name_for_nick, _not_menu_text)
async def create_nick_finish(message: Message, state: FSMContext) -> None:
    """Kiritilgan ism asosida bir nechta stilize qilingan nik yaratadi."""
    name = message.text.strip()
    await state.clear()

    if not name:
        await message.answer("⚠️ Ism bo'sh bo'lishi mumkin emas.")
        return

    lines = [f"• <code>{template.format(name=name)}</code>" for template in NICK_TEMPLATES]
    text = "🎮 <b>Siz uchun niklar:</b>\n\n" + "\n".join(lines)
    await message.answer(text)


# ------------------------------------------------------------------ #
# 🎲 Random Nik
# ------------------------------------------------------------------ #

@router.message(F.text == BTN_RANDOM_NICK)
async def random_nick(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()

    nick = await db.get_random_nick()
    nick_text = nick.nick if nick else random.choice(DEFAULT_NICKS)

    await message.answer(
        f"🎲 Tasodifiy nik:\n\n<code>{nick_text}</code>",
        reply_markup=favorite_button(nick_text),
    )


# ------------------------------------------------------------------ #
# 📋 Tayyor Niklar (sahifalab)
# ------------------------------------------------------------------ #

@router.message(F.text == BTN_READY_NICKS)
async def ready_nicks(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()
    await _send_nicks_page(message, db, page=0)


@router.callback_query(F.data.startswith("nicks_page:"))
async def ready_nicks_page(callback: CallbackQuery, db: Database) -> None:
    """Sahifalash tugmalari bosilganda xabarni tahrirlaydi."""
    page = int(callback.data.split(":", 1)[1])
    await _send_nicks_page(callback.message, db, page=page, edit=True)
    await callback.answer()


async def _send_nicks_page(
    message: Message, db: Database, page: int, edit: bool = False
) -> None:
    nicks, total_pages = await db.get_nicks_page(page, per_page=10)

    if not nicks:
        text = "📋 <b>Tayyor Niklar</b>\n\n" + "\n".join(
            f"• <code>{n}</code>" for n in DEFAULT_NICKS
        )
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return

    lines = [f"• <code>{n.nick}</code>" for n in nicks]
    text = "📋 <b>Tayyor Niklar</b>\n\n" + "\n".join(lines)
    keyboard = pagination_keyboard(page, total_pages)

    if edit:
        await message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


# ------------------------------------------------------------------ #
# 🔍 Nik qidirish
# ------------------------------------------------------------------ #

@router.message(F.text == BTN_SEARCH_NICK)
async def search_nick_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(UserStates.waiting_search_term)
    await message.answer(
        "🔍 Qidirmoqchi bo'lgan nik nomini (yoki bir qismini) yuboring.\n"
        "Bekor qilish uchun /cancel yozing."
    )


@router.message(UserStates.waiting_search_term, _not_menu_text)
async def search_nick_finish(
    message: Message, state: FSMContext, db: Database
) -> None:
    term = message.text.strip()
    await state.clear()

    results = await db.search_nicks(term, limit=20)

    if not results:
        await message.answer(f"😕 <code>{term}</code> bo'yicha hech narsa topilmadi.")
        return

    lines = [f"• <code>{n.nick}</code>" for n in results]
    text = f"🔍 <b>Qidiruv natijalari</b> ({len(results)} ta):\n\n" + "\n".join(lines)
    await message.answer(text)


# ------------------------------------------------------------------ #
# ❤️ Sevimli Niklar
# ------------------------------------------------------------------ #

@router.message(F.text == BTN_FAVORITES)
async def show_favorites(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()

    favorites = await db.get_favorites(message.from_user.id)

    if not favorites:
        await message.answer(
            "❤️ Sizda hali sevimli niklar yo'q.\n\n"
            "Random yoki qidiruv natijasidagi nik ostidagi "
            "«❤️ Sevimlilarga qo'shish» tugmasini bosib qo'shishingiz mumkin."
        )
        return

    text = "❤️ <b>Sevimli niklaringiz</b> (o'chirish uchun bosing):"
    await message.answer(text, reply_markup=favorites_list_keyboard(favorites))


@router.callback_query(F.data.startswith("fav_add:"))
async def add_favorite(callback: CallbackQuery, db: Database) -> None:
    nick_text = callback.data.split(":", 1)[1]
    added = await db.add_favorite(callback.from_user.id, nick_text)

    if added:
        await callback.answer("❤️ Sevimlilarga qo'shildi!")
    else:
        await callback.answer("ℹ️ Bu nik allaqachon sevimlilarda.")


@router.callback_query(F.data.startswith("fav_del:"))
async def remove_favorite(callback: CallbackQuery, db: Database) -> None:
    favorite_id = int(callback.data.split(":", 1)[1])
    removed = await db.remove_favorite(callback.from_user.id, favorite_id)

    if removed:
        favorites = await db.get_favorites(callback.from_user.id)
        if favorites:
            await callback.message.edit_reply_markup(
                reply_markup=favorites_list_keyboard(favorites)
            )
        else:
            await callback.message.edit_text("❤️ Sevimli niklar ro'yxati bo'sh.")
        await callback.answer("🗑 O'chirildi.")
    else:
        await callback.answer("⚠️ Topilmadi.")


# ------------------------------------------------------------------ #
# 🏆 Top Niklar
# ------------------------------------------------------------------ #

@router.message(F.text == BTN_TOP_NICKS)
async def top_nicks(message: Message, state: FSMContext, db: Database) -> None:
    await state.clear()

    results = await db.get_top_nicks(limit=10)

    if not results:
        await message.answer(
            "🏆 Hozircha statistikaga ega niklar yo'q. "
            "Random Nik orqali niklarni ko'ring — shu yerda "
            "eng mashhurlari to'planadi."
        )
        return

    lines = [f"{i}. <code>{n.nick}</code> — {n.picks} marta" for i, n in enumerate(results, 1)]
    text = "🏆 <b>Top Niklar</b>\n\n" + "\n".join(lines)
    await message.answer(text)


# ------------------------------------------------------------------ #
# ✨ Ko'rinmas belgi
# ------------------------------------------------------------------ #

@router.message(F.text == BTN_INVISIBLE)
async def invisible_char(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "👇 Nusxalang:\n\n<code>ㅤ</code>\n\n"
        "Bu Free Fire uchun ko'rinmas belgidir."
    )


# ------------------------------------------------------------------ #
# Erkin matn — hech qaysi state va tugmaga to'g'ri kelmagan xabarlar
# ------------------------------------------------------------------ #

@router.message(F.text & ~F.text.startswith("/"))
async def fallback_hint(message: Message, state: FSMContext) -> None:
    """
    Foydalanuvchi hech qanday faol jarayonsiz, tushunarsiz matn
    yuborsa shu yerga tushadi. Eski kodda bu handler har qanday
    matnni "ism" deb generatsiya qilardi — bu chalkash edi.
    Endi aniq yo'l-yo'riq beramiz.
    """
    await state.clear()
    await message.answer(
        "🤔 Buni tushunmadim.\n\n"
        "Nik yaratish uchun 🎮 <b>Nik yaratish</b> tugmasini bosing "
        "yoki quyidagi menyudan foydalaning."
    )
