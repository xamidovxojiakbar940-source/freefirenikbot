"""
handlers/__init__.py
=====================
Barcha routerlarni yig'ib, YAGONA to'g'ri tartibda ulaydigan modul.

BU FAYL ESKI BUGNI TUZATISHNING MARKAZIY QISMI.

Nima uchun tartib muhim:
    aiogram har bir yangilanishni routerlar bo'ylab RO'YXATDAN
    O'TISH TARTIBIDA tekshiradi va birinchi mos kelgan handlerda
    to'xtaydi. Eski kodda FSM-kutish handlerlari (masalan "nikni
    kutish") hech qanday matn cheklovisiz edi va tasodifan boshqa
    tugma handlerlaridan OLDIN tekshirilardi — shu sabab har qanday
    tugma bosilsa ham FSM ichiga "yutilib" ketardi.

    Yechim ikki qavatli:
      1) `common_router` — /start, /cancel va navigatsiya — ENG
         BIRINCHI bo'lib tekshiriladi va har doim `state.clear()`
         chaqiradi.
      2) `admin_router` va `user_router` ichida har bir "kutish"
         handleri `keyboards.ALL_MENU_TEXTS` ro'yxatidagi matnlarni
         ANIQ chetlab o'tadi (bunday matn kelsa, handler shunchaki
         ishlamaydi va navbat asosiy tugma handleriga o'tadi).

    Natijada: foydalanuvchi qaysi state'da bo'lishidan qat'iy nazar,
    biror menyu tugmasini bossa — u har doim to'g'ri amalga boradi.
"""

from aiogram import Router

from .admin import router as admin_router
from .common import router as common_router
from .user import router as user_router

router = Router(name="root")

# TARTIB MUHIM: common -> admin -> user
router.include_router(common_router)
router.include_router(admin_router)
router.include_router(user_router)

__all__ = ["router"]
