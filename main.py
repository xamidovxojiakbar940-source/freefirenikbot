"""
main.py
=======
Botning kirish nuqtasi.

Talab #25 bo'yicha ("Bot qayta ishga tushganda hech qanday state
saqlanib qolmasin"): `MemoryStorage` ishlatilgani uchun bot qayta
ishga tushganda barcha FSM holatlari xotiradan avtomatik tozalanadi
— fayl yoki tashqi bazada saqlanmaydi. Agar botni bir nechta server
nusxasida (masalan Railway'da ko'p worker bilan) ishga tushirish kerak
bo'lsa, `RedisStorage` ga o'tish tavsiya etiladi (pastdagi izohga
qarang), lekin bitta instansiya uchun `MemoryStorage` yetarli va eng
tez variant.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from database import Database
from errors import register_error_handlers
from handlers import router


def setup_logging() -> None:
    """Bot logging tizimini sozlaydi."""
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        stream=sys.stdout,
    )
    # aiohttp/aiogram ichki kutubxonalarining ortiqcha DEBUG loglarini
    # bosib qo'yamiz, faqat WARNING va undan yuqorisini ko'rsatamiz.
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


async def main() -> None:
    setup_logging()
    logger = logging.getLogger(__name__)

    db = Database(settings.db_path)
    await db.connect()
    logger.info("✅ Baza ulandi: %s", settings.db_path)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # MemoryStorage — har bir foydalanuvchining FSM holati (chat_id +
    # user_id bo'yicha) alohida saqlanadi, shuning uchun bir
    # foydalanuvchining state'i boshqasiga hech qachon ta'sir qilmaydi
    # (talab #17).
    dp = Dispatcher(storage=MemoryStorage())

    # `db` va `settings` obyektlarini har bir handlerga avtomatik
    # inject qilish uchun workflow_data'ga qo'shamiz. Endi istalgan
    # handler funksiyasi `db: Database` yoki `settings: Settings`
    # parametrini qo'shib, ularga to'g'ridan-to'g'ri murojaat qila oladi.
    dp["db"] = db
    dp["settings"] = settings

    dp.include_router(router)
    register_error_handlers(dp)

    try:
        # Eski, ishlatilmagan update'larni (bot o'chiq turgan paytdagi)
        # tashlab yuborish — qayta ishga tushganda eskirgan xabarlarga
        # javob berib, foydalanuvchini chalg'itmaslik uchun.
        await bot.delete_webhook(drop_pending_updates=True)

        logger.info("✅ Bot ishga tushdi (@%s)", (await bot.get_me()).username)
        await dp.start_polling(bot)
    finally:
        await db.close()
        await bot.session.close()
        logger.info("🛑 Bot to'xtatildi, resurslar tozalandi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("🛑 Bot qo'lda to'xtatildi.")
