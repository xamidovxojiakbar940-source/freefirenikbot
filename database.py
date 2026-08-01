import aiosqlite

DB_NAME = "database.db"


async def init_db():

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS users(

            user_id INTEGER PRIMARY KEY,
            full_name TEXT

        )
        """)

        await db.execute("""
        CREATE TABLE IF NOT EXISTS nicks(

            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nick TEXT

        )
        """)

        await db.commit()


async def add_user(user_id, full_name):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(

            "INSERT OR IGNORE INTO users(user_id,full_name) VALUES(?,?)",

            (user_id, full_name)

        )

        await db.commit()


async def get_users_count():

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(

            "SELECT COUNT(*) FROM users"

        )

        data = await cursor.fetchone()

        return data[0]


async def add_nick(nick):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(

            "INSERT INTO nicks(nick) VALUES(?)",

            (nick,)

        )

        await db.commit()


async def delete_nick(nick):

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(

            "DELETE FROM nicks WHERE nick=?",

            (nick,)

        )

        await db.commit()


async def get_nicks():

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(

            "SELECT nick FROM nicks"

        )

        return await cursor.fetchall()