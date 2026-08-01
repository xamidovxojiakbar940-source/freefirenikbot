"""
config.py
=========
Botning barcha sozlamalari shu yerda markazlashtirilgan.

MUHIM (xavfsizlik):
    Eski loyihada BOT_TOKEN config.py fayli ichiga TO'G'RIDAN-TO'G'RI
    yozib qo'yilgan edi. Bu juda xavfli — token GitHub'ga tushib qolsa,
    botni istalgan kishi o'g'irlab olishi mumkin.

    Shuning uchun endi barcha maxfiy ma'lumotlar (.env) faylidan
    o'qiladi. .env fayli hech qachon Git'ga qo'shilmaydi
    (.gitignore ga qarang).

Railway'da deploy qilganda BOT_TOKEN va ADMIN_IDS qiymatlarini
Railway "Variables" bo'limiga kiritish kifoya — .env fayli shart emas.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

from dotenv import load_dotenv

# .env faylini yuklaymiz (agar mavjud bo'lsa). Railway kabi muhitlarda
# .env fayli bo'lmasligi mumkin — bu holatda tizim environment
# o'zgaruvchilaridan foydalaniladi, xatolik bermaydi.
load_dotenv()


def _parse_admin_ids(raw: str | None) -> frozenset[int]:
    """
    "123456789,987654321" ko'rinishidagi satrni Telegram ID'lar
    to'plamiga (set) aylantiradi. Bo'sh yoki noto'g'ri qiymatlarni
    e'tiborsiz qoldiradi.
    """
    if not raw:
        return frozenset()

    ids: set[int] = set()
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ids.add(int(chunk))
        except ValueError:
            continue
    return frozenset(ids)


@dataclass(frozen=True, slots=True)
class Settings:
    """Bot ishlashi uchun zarur bo'lgan barcha sozlamalar."""

    bot_token: str
    admin_ids: frozenset[int] = field(default_factory=frozenset)
    db_path: str = "database.db"
    nicks_per_page: int = 10          # "Tayyor Niklar" sahifalash uchun
    search_result_limit: int = 20     # "Nik qidirish" natijalari soni
    log_level: str = "INFO"

    def is_admin(self, user_id: int) -> bool:
        """Berilgan user_id admin ekanligini tekshiradi."""
        return user_id in self.admin_ids


def load_settings() -> Settings:
    """
    Environment o'zgaruvchilaridan Settings obyektini yig'adi.
    BOT_TOKEN topilmasa, bot ishga tushmasdan aniq xato bilan to'xtaydi
    (noto'g'ri tokendan keyinroq tushunarsiz xato olishdan yaxshiroq).
    """
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        sys.exit(
            "❌ BOT_TOKEN topilmadi.\n"
            "   .env faylida (yoki Railway Variables bo'limida) "
            "BOT_TOKEN=... qiymatini kiriting.\n"
            "   Namuna uchun .env.example fayliga qarang."
        )

    admin_ids = _parse_admin_ids(os.getenv("ADMIN_IDS") or os.getenv("ADMIN_ID"))
    if not admin_ids:
        # Bot baribir ishga tushadi, lekin admin panel hech kimga
        # ochilmaydi — bu haqda ogohlantiramiz.
        print(
            "⚠️  ADMIN_IDS ko'rsatilmagan. Admin panelga hech kim "
            "kira olmaydi. .env faylida ADMIN_IDS=123456789 kabi "
            "kiriting (bir nechta admin uchun vergul bilan ajrating)."
        )

    return Settings(
        bot_token=token,
        admin_ids=admin_ids,
        db_path=os.getenv("DB_PATH", "database.db"),
        nicks_per_page=int(os.getenv("NICKS_PER_PAGE", "10")),
        search_result_limit=int(os.getenv("SEARCH_RESULT_LIMIT", "20")),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    )


# Butun loyiha bo'ylab shu bitta obyekt import qilinadi.
settings = load_settings()
