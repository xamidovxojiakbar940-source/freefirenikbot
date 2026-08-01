"""
handlers/admin.py
==================
Admin panel: statistika, foydalanuvchilar soni, broadcast, nik
qo'shish/o'chirish, backup.

MUHIM QOIDA (eski bugni butunlay yo'qotish uchun):
    Har bir "kutish" (FSM) handleri quyidagi filtr bilan himoyalangan:

        F.text.func(lambda text: text not in ALL_MENU_TEXTS)

    Bu degani: agar foydalanuvchi biror amal kutilayotgan paytda
    (masalan, "yangi nikni yuboring" deb kutilganda) o'rniga biror
    menyu tugmasini bossa, bu handler ISHLAMAYDI va navbat haqiqiy
    tugma handleriga o'tadi (chunki u handlers/__init__.py da keyinroq
    tekshiriladi). Shu tariqa "Random Nik" tugmasi hech qachon
    "Nik o'chirish" holatiga yutilib qolmaydi.
"""

import asyncio
import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from config import Settings
from database import Database
from keyboards import (
    ALL_MENU_TEXTS,
    BTN_ADD_NICK,
    BTN_BACKUP,
    BTN_BROADCAST,
    BTN_DELETE_NICK,
    BTN_STATS,
    BTN_USERS_COUNT,
    admin_menu,
)
from states import AdminStates

logger = logging.getLogger(__name__)

router = Router(name="admin")


def _not_menu_text(message: Message) -> bool:
    """
    FSM "kutish" handlerlari uchun himoya filtri.

    Matn bo'sh bo'lsa yoki menyu tugmalaridan biriga teng bo'lsa,
    False qaytaradi — shunda handler ishga tushmaydi va navbat
    haqiqiy tugma handleriga (masalan user_router dagi) o'tadi.
    """
    return bool(message.text) and message.text not in ALL_MENU_TEXTS


# ------------------------------------------------------------------ #
# 📊 Statistika / 👥 Foydalanuvchilar soni
# ------------------------------------------------------------------ #

@router.message(F.text == BTN_STATS)
async def show_statistics(
    message: Message, state: FSMContext, db: Database, settings: Settings
) -> None:
    """To'liq statistika: foydalanuvchilar va niklar soni."""
    if not settings.is_admin(message.from_user.id):
        return
    await state.clear()

    users_count = await db.get_users_count()
    nicks_count = await db.count_nicks()

    await message.answer(
        "📊 <b>Bot statistikasi</b>\n\n"
        f"👥 Foydalanuvchilar: <b>{users_count}</b>\n"
        f"🎮 Bazadagi niklar: <b>{nicks_count}</b>"
    )


@router.message(F.text == BTN_USERS_COUNT)
async def show_users_count(
    message: Message, state: FSMContext, db: Database, settings: Settings
) -> None:
    """Faqat foydalanuvchilar sonini ko'rsatadi (talab #20)."""
    if not settings.is_admin(message.from_user.id):
        return
    await state.clear()

    count = await db.get_users_count()
    await message.answer(f"👥 Jami foydalanuvchilar: <b>{count}</b>")


# ------------------------------------------------------------------ #
# 📢 Broadcast
# ------------------------------------------------------------------ #

@router.message(F.text == BTN_BROADCAST)
async def broadcast_start(
    message: Message, state: FSMContext, settings: Settings
) -> None:
    if not settings.is_admin(message.from_user.id):
        return
    await state.clear()
    await state.set_state(AdminStates.waiting_broadcast)
    await message.answer(
        "📨 Barcha foydalanuvchilarga yuboriladigan xabarni yuboring.\n"
        "Bekor qilish uchun /cancel yozing."
    )


@router.message(AdminStates.waiting_broadcast, _not_menu_text)
async def broadcast_send(
    message: Message, state: FSMContext, db: Database, settings: Settings
) -> None:
    """
    Xabarni barcha foydalanuvchilarga yuboradi.

    Botni bloklab qo'ygan foydalanuvchilar (`TelegramForbiddenError`)
    va Telegram flood-limit (`TelegramRetryAfter`) alohida ushlanadi —
    shu tufayli bitta xato butun broadcast jarayonini to'xtatib
    qo'ymaydi (talab #5, exception handling).
    """
    if not settings.is_admin(message.from_user.id):
        return

    user_ids = await db.get_all_user_ids()
    bot = message.bot

    success, failed = 0, 0

    for user_id in user_ids:
        try:
            await message.copy_to(chat_id=user_id)
            success += 1
        except TelegramRetryAfter as exc:
            # Flood limitga tegib ketsak, ko'rsatilgan vaqtcha kutamiz
            # va shu foydalanuvchiga qayta urinamiz.
            await asyncio.sleep(exc.retry_after)
            try:
                await message.copy_to(chat_id=user_id)
                success += 1
            except Exception:  # noqa: BLE001 - broadcastni to'xtatmaslik uchun
                failed += 1
        except TelegramForbiddenError:
            # Foydalanuvchi botni bloklagan — kutilgan holat, xato emas.
            failed += 1
        except Exception:  # noqa: BLE001
            logger.exception("Broadcast xatosi user_id=%s", user_id)
            failed += 1

    await state.clear()
    await message.answer(
        f"✅ Broadcast yakunlandi.\n\n"
        f"Yuborildi: <b>{success}</b>\n"
        f"Yuborilmadi: <b>{failed}</b>",
        reply_markup=admin_menu(),
    )


# ------------------------------------------------------------------ #
# ➕ Nik qo'shish
# ------------------------------------------------------------------ #

@router.message(F.text == BTN_ADD_NICK)
async def add_nick_start(
    message: Message, state: FSMContext, settings: Settings
) -> None:
    if not settings.is_admin(message.from_user.id):
        return
    await state.clear()
    await state.set_state(AdminStates.waiting_new_nick)
    await message.answer(
        "➕ Yangi nikni yuboring (bitta xabarda bitta nik).\n"
        "Bekor qilish uchun /cancel yozing."
    )


@router.message(AdminStates.waiting_new_nick, _not_menu_text)
async def add_nick_save(
    message: Message, state: FSMContext, db: Database, settings: Settings
) -> None:
    if not settings.is_admin(message.from_user.id):
        return

    nick_text = message.text.strip()
    added = await db.add_nick(nick_text)
    await state.clear()

    if added:
        await message.answer(
            f"✅ Nik bazaga qo'shildi:\n<code>{nick_text}</code>",
            reply_markup=admin_menu(),
        )
    else:
        await message.answer(
            "⚠️ Bunday nik allaqachon bazada mavjud.",
            reply_markup=admin_menu(),
        )


# ------------------------------------------------------------------ #
# ❌ Nik o'chirish
# ------------------------------------------------------------------ #

@router.message(F.text == BTN_DELETE_NICK)
async def delete_nick_start(
    message: Message, state: FSMContext, settings: Settings
) -> None:
    if not settings.is_admin(message.from_user.id):
        return
    await state.clear()
    await state.set_state(AdminStates.waiting_delete_nick)
    await message.answer(
        "❌ O'chiriladigan nikni aynan bazadagidek yuboring.\n"
        "Bekor qilish uchun /cancel yozing."
    )


@router.message(AdminStates.waiting_delete_nick, _not_menu_text)
async def delete_nick_finish(
    message: Message, state: FSMContext, db: Database, settings: Settings
) -> None:
    if not settings.is_admin(message.from_user.id):
        return

    nick_text = message.text.strip()
    deleted = await db.delete_nick(nick_text)
    await state.clear()

    if deleted:
        await message.answer(
            f"✅ Nik o'chirildi:\n<code>{nick_text}</code>",
            reply_markup=admin_menu(),
        )
    else:
        await message.answer(
            "⚠️ Bunday nik bazada topilmadi.",
            reply_markup=admin_menu(),
        )


# ------------------------------------------------------------------ #
# 💾 Backup
# ------------------------------------------------------------------ #

@router.message(F.text == BTN_BACKUP)
async def backup_database(
    message: Message, state: FSMContext, db: Database, settings: Settings
) -> None:
    if not settings.is_admin(message.from_user.id):
        return
    await state.clear()

    await message.answer("💾 Backup tayyorlanmoqda...")
    try:
        backup_path = await db.backup()
        await message.answer_document(
            FSInputFile(backup_path),
            caption=f"✅ Backup: <code>{backup_path.name}</code>",
        )
    except Exception:  # noqa: BLE001
        logger.exception("Backup yaratishda xatolik")
        await message.answer("❌ Backup yaratishda xatolik yuz berdi.")
