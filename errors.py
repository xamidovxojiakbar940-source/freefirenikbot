"""
errors.py
=========
Global xatoliklarni ushlovchi handler.

Eski kodda hech qanday global exception handling yo'q edi — birorta
handler ichida kutilmagan xatolik (masalan bazaga ulanish uzilib
qolishi) yuz bersa, bot butunlay to'xtab qolishi yoki foydalanuvchi
hech qanday javob olmay qolishi mumkin edi (talab #5).

Bu modul har qanday ushlanmagan xatolikni logga yozadi va, imkon
bo'lsa, foydalanuvchiga tushunarli xabar yuboradi — bot esa ishlashda
davom etadi.
"""

import logging

from aiogram import Dispatcher
from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)


def register_error_handlers(dp: Dispatcher) -> None:
    """Dispatcher'ga global xato handlerini ulaydi."""

    @dp.errors()
    async def handle_all_errors(event: ErrorEvent) -> bool:
        logger.exception(
            "Kutilmagan xatolik: update_id=%s",
            event.update.update_id,
            exc_info=event.exception,
        )

        update = event.update
        message = update.message or (
            update.callback_query.message if update.callback_query else None
        )

        if message is not None:
            try:
                await message.answer(
                    "⚠️ Kutilmagan xatolik yuz berdi. Iltimos, qaytadan "
                    "urinib ko'ring yoki /start bosing."
                )
            except Exception:  # noqa: BLE001 - foydalanuvchiga xabar yuborish shart emas
                logger.exception("Xato xabarini yuborib bo'lmadi")

        # True qaytarish — xatolik "boshqarildi" deb belgilanadi, bot
        # yiqilmaydi va keyingi yangilanishlarni qabul qilishda davom etadi.
        return True
