"""
states.py
=========
Botning barcha FSM (Finite State Machine) holatlari shu yerda
markazlashtirilgan. Bu handlers/ paketidagi barcha fayllar bir xil
state'larga murojaat qila olishini ta'minlaydi va aylanma import
(circular import) muammosining oldini oladi.
"""

from aiogram.fsm.state import State, StatesGroup


class AdminStates(StatesGroup):
    """Admin panelidagi ko'p bosqichli amallar uchun holatlar."""

    waiting_broadcast = State()   # 📢 Broadcast matnini kutish
    waiting_new_nick = State()    # ➕ Yangi nik matnini kutish
    waiting_delete_nick = State()  # ❌ O'chiriladigan nik matnini kutish


class UserStates(StatesGroup):
    """Oddiy foydalanuvchi uchun ko'p bosqichli amallar."""

    waiting_name_for_nick = State()  # 🎮 Nik yaratish uchun ism kutish
    waiting_search_term = State()    # 🔍 Qidiruv so'zini kutish
