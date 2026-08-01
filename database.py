"""
database.py
============
Botning butun SQLite qatlami shu yerda.

Eskisiga nisbatan nima o'zgardi va NEGA:

1. Har bir funksiya o'zining `aiosqlite.connect(...)` ulanishini
   ochib-yopardi. Bu sekin va resurs isrofgarchiligi edi (har bir
   so'rov uchun fayl ochish/yopish). Endi bitta doimiy ulanish
   (`self._conn`) butun bot hayoti davomida ochiq turadi va
   qayta ishlatiladi — bu tezlikni sezilarli oshiradi.
2. `PRAGMA journal_mode=WAL` yoqildi — o'qish va yozish bir vaqtda
   bir-biriga xalaqit bermaydi (bir nechta foydalanuvchi bir vaqtda
   so'rov yuborsa ham bot qotib qolmaydi).
3. `nicks.nick` ustuniga UNIQUE INDEX qo'yildi — takroriy niklar
   bazaga qo'shilib ketmaydi va qidiruv tezlashadi.
4. Qidiruv (`search_nicks`) endi indekslangan `LIKE ... COLLATE NOCASE`
   orqali ishlaydi — Unicode belgili niklarda ham tez ishlaydi.
5. Yangi jadvallar: `favorites` (Sevimli Niklar) va `nicks.picks`
   ustuni (Top Niklar uchun mashhurlik hisoblagichi).
6. Yozish operatsiyalari `asyncio.Lock` bilan himoyalangan — bir nechta
   so'rov bir vaqtda kelsa ham SQLite "database is locked" xatosini
   bermaydi.
7. Barcha SQL parametrlari `?` orqali beriladi (SQL Injection'dan
   himoya) — bu eski kodda ham to'g'ri edi, shu yondashuv saqlab
   qolindi va kengaytirildi.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite


@dataclass(slots=True)
class Nick:
    """Bitta nik yozuvini ifodalaydi."""

    id: int
    nick: str
    picks: int = 0


class Database:
    """
    Bot uchun yagona SQLite ulanishini boshqaruvchi klass.

    Ishlatilishi:
        db = Database(path)
        await db.connect()
        ...
        await db.close()
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: aiosqlite.Connection | None = None
        self._write_lock = asyncio.Lock()

    # ------------------------------------------------------------------ #
    # Ulanish boshqaruvi
    # ------------------------------------------------------------------ #

    async def connect(self) -> None:
        """Bazaga ulanadi, kerakli jadval va indekslarni yaratadi."""
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row

        await self._conn.execute("PRAGMA journal_mode=WAL;")
        await self._conn.execute("PRAGMA foreign_keys=ON;")
        await self._create_schema()

    async def close(self) -> None:
        """Ulanishni yopadi (bot to'xtaganda chaqiriladi)."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError(
                "Database ulanmagan. Avval `await db.connect()` chaqiring."
            )
        return self._conn

    async def _create_schema(self) -> None:
        """
        Jadval va indekslarni yaratadi.

        Eslatma (eski bazadan ko'chirish): agar `database.db` avvalgi
        loyihadan qolgan bo'lsa, undagi `nicks` jadvalida `picks`
        ustuni va `UNIQUE` cheklovi yo'q edi. `CREATE TABLE IF NOT
        EXISTS` mavjud jadvalni o'zgartirmasligi sababli, bu yerda
        qo'shimcha migratsiya qadami (`_migrate_legacy_nicks_table`)
        bajariladi — eski baza bilan ham bot xatosiz ishlaydi.
        """
        await self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                full_name   TEXT NOT NULL,
                joined_at   TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS nicks (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                nick    TEXT NOT NULL UNIQUE,
                picks   INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS favorites (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                nick_text   TEXT NOT NULL,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (user_id, nick_text)
            );

            CREATE INDEX IF NOT EXISTS idx_favorites_user
                ON favorites (user_id);
            """
        )
        await self.conn.commit()

        await self._migrate_legacy_nicks_table()
        await self._ensure_nicks_indexes()

    async def _migrate_legacy_nicks_table(self) -> None:
        """Eski (picks ustunisiz) `nicks` jadvalini yangi sxemaga moslaydi."""
        cursor = await self.conn.execute("PRAGMA table_info(nicks)")
        columns = {row["name"] for row in await cursor.fetchall()}

        if "picks" not in columns:
            await self.conn.execute(
                "ALTER TABLE nicks ADD COLUMN picks INTEGER NOT NULL DEFAULT 0"
            )
            await self.conn.commit()
            logging.getLogger(__name__).info(
                "Migratsiya: 'nicks.picks' ustuni qo'shildi."
            )

    async def _ensure_nicks_indexes(self) -> None:
        """
        Tezlik uchun indekslarni yaratadi. Eski bazada takrorlanuvchi
        niklar bo'lsa, UNIQUE indeks yaratib bo'lmaydi — bunday holatda
        avval dublikatlarni tozalaymiz, keyin qayta urinamiz.
        """
        try:
            await self.conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_nicks_nick_nocase "
                "ON nicks (nick COLLATE NOCASE)"
            )
        except aiosqlite.IntegrityError:
            logging.getLogger(__name__).warning(
                "Bazada takroriy niklar topildi — dublikatlar tozalanmoqda."
            )
            await self.conn.execute(
                """
                DELETE FROM nicks
                WHERE id NOT IN (
                    SELECT MIN(id) FROM nicks GROUP BY nick COLLATE NOCASE
                )
                """
            )
            await self.conn.commit()
            await self.conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_nicks_nick_nocase "
                "ON nicks (nick COLLATE NOCASE)"
            )

        await self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_nicks_picks ON nicks (picks DESC)"
        )
        await self.conn.commit()

    # ------------------------------------------------------------------ #
    # Foydalanuvchilar
    # ------------------------------------------------------------------ #

    async def add_user(self, user_id: int, full_name: str) -> None:
        """Yangi foydalanuvchini qo'shadi (mavjud bo'lsa, e'tiborsiz)."""
        async with self._write_lock:
            await self.conn.execute(
                "INSERT OR IGNORE INTO users (user_id, full_name) "
                "VALUES (?, ?)",
                (user_id, full_name),
            )
            await self.conn.commit()

    async def get_users_count(self) -> int:
        cursor = await self.conn.execute("SELECT COUNT(*) FROM users")
        row = await cursor.fetchone()
        return row[0] if row else 0

    async def get_all_user_ids(self) -> list[int]:
        """Broadcast yuborish uchun barcha foydalanuvchi ID'lari."""
        cursor = await self.conn.execute("SELECT user_id FROM users")
        rows = await cursor.fetchall()
        return [row[0] for row in rows]

    # ------------------------------------------------------------------ #
    # Niklar (admin CRUD)
    # ------------------------------------------------------------------ #

    async def add_nick(self, nick: str) -> bool:
        """
        Yangi nikni bazaga qo'shadi.
        Returns:
            True  — muvaffaqiyatli qo'shildi
            False — bunday nik allaqachon mavjud (UNIQUE cheklov)
        """
        async with self._write_lock:
            try:
                await self.conn.execute(
                    "INSERT INTO nicks (nick) VALUES (?)", (nick,)
                )
                await self.conn.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def delete_nick(self, nick: str) -> bool:
        """
        Nikni o'chiradi.
        Returns:
            True  — o'chirildi
            False — bunday nik topilmadi
        """
        async with self._write_lock:
            cursor = await self.conn.execute(
                "DELETE FROM nicks WHERE nick = ? COLLATE NOCASE", (nick,)
            )
            await self.conn.commit()
            return cursor.rowcount > 0

    async def count_nicks(self) -> int:
        cursor = await self.conn.execute("SELECT COUNT(*) FROM nicks")
        row = await cursor.fetchone()
        return row[0] if row else 0

    # ------------------------------------------------------------------ #
    # Niklar (foydalanuvchi uchun)
    # ------------------------------------------------------------------ #

    async def get_random_nick(self) -> Nick | None:
        """Bazadan tasodifiy bitta nik qaytaradi va mashhurligini oshiradi."""
        cursor = await self.conn.execute(
            "SELECT id, nick, picks FROM nicks "
            "ORDER BY RANDOM() LIMIT 1"
        )
        row = await cursor.fetchone()
        if row is None:
            return None

        nick = Nick(id=row["id"], nick=row["nick"], picks=row["picks"])
        await self._increment_picks(nick.id)
        return nick

    async def get_nicks_page(self, page: int, per_page: int) -> tuple[list[Nick], int]:
        """
        "Tayyor Niklar" ro'yxatini sahifalab qaytaradi.

        Returns:
            (shu sahifadagi niklar, jami sahifalar soni)
        """
        total = await self.count_nicks()
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(0, min(page, total_pages - 1))

        cursor = await self.conn.execute(
            "SELECT id, nick, picks FROM nicks "
            "ORDER BY id LIMIT ? OFFSET ?",
            (per_page, page * per_page),
        )
        rows = await cursor.fetchall()
        nicks = [Nick(id=r["id"], nick=r["nick"], picks=r["picks"]) for r in rows]
        return nicks, total_pages

    async def search_nicks(self, term: str, limit: int) -> list[Nick]:
        """
        Nik nomi bo'yicha tez qidiruv.
        `COLLATE NOCASE` + indeks tufayli katta bazada ham tez ishlaydi.
        """
        term = term.strip()
        if not term:
            return []

        pattern = f"%{term}%"
        cursor = await self.conn.execute(
            "SELECT id, nick, picks FROM nicks "
            "WHERE nick LIKE ? COLLATE NOCASE "
            "ORDER BY picks DESC LIMIT ?",
            (pattern, limit),
        )
        rows = await cursor.fetchall()
        return [Nick(id=r["id"], nick=r["nick"], picks=r["picks"]) for r in rows]

    async def get_top_nicks(self, limit: int = 10) -> list[Nick]:
        """Eng ko'p ko'rilgan (picks) niklar ro'yxati."""
        cursor = await self.conn.execute(
            "SELECT id, nick, picks FROM nicks "
            "WHERE picks > 0 ORDER BY picks DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [Nick(id=r["id"], nick=r["nick"], picks=r["picks"]) for r in rows]

    async def _increment_picks(self, nick_id: int) -> None:
        async with self._write_lock:
            await self.conn.execute(
                "UPDATE nicks SET picks = picks + 1 WHERE id = ?", (nick_id,)
            )
            await self.conn.commit()

    # ------------------------------------------------------------------ #
    # Sevimli niklar
    # ------------------------------------------------------------------ #

    async def add_favorite(self, user_id: int, nick_text: str) -> bool:
        """
        Nikni foydalanuvchining sevimlilariga qo'shadi.
        Returns False agar allaqachon sevimlida bo'lsa.
        """
        async with self._write_lock:
            try:
                await self.conn.execute(
                    "INSERT INTO favorites (user_id, nick_text) "
                    "VALUES (?, ?)",
                    (user_id, nick_text),
                )
                await self.conn.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def remove_favorite(self, user_id: int, favorite_id: int) -> bool:
        async with self._write_lock:
            cursor = await self.conn.execute(
                "DELETE FROM favorites WHERE id = ? AND user_id = ?",
                (favorite_id, user_id),
            )
            await self.conn.commit()
            return cursor.rowcount > 0

    async def get_favorites(self, user_id: int) -> list[aiosqlite.Row]:
        cursor = await self.conn.execute(
            "SELECT id, nick_text FROM favorites "
            "WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        )
        return await cursor.fetchall()

    # ------------------------------------------------------------------ #
    # Backup
    # ------------------------------------------------------------------ #

    async def backup(self, destination_dir: str = ".") -> Path:
        """
        Bazaning nusxasini yaratadi va yo'lini qaytaradi.
        SQLite fayli ustida ishlayotgan bo'lsak ham xavfsiz bo'lishi
        uchun avval barcha yozuvlarni commit qilamiz (WAL checkpoint).
        """
        async with self._write_lock:
            await self.conn.execute("PRAGMA wal_checkpoint(FULL);")
            await self.conn.commit()

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        dest = Path(destination_dir) / f"backup_{timestamp}.db"
        # Fayl nusxalash sinxron amal — event loopni bloklamasligi uchun
        # alohida threadga chiqaramiz.
        await asyncio.to_thread(shutil.copyfile, self._db_path, dest)
        return dest
