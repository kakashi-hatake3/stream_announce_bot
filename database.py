import aiosqlite
import logging

DB_NAME = "bot.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                twitch_login TEXT NOT NULL,
                is_live INTEGER DEFAULT 0,
                UNIQUE(chat_id, twitch_login)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS templates (
                chat_id INTEGER NOT NULL,
                twitch_login TEXT NOT NULL,
                template TEXT NOT NULL,
                PRIMARY KEY (chat_id, twitch_login)
            )
        """)
        await db.commit()

async def add_subscription(chat_id: int, twitch_login: str):
    async with aiosqlite.connect(DB_NAME) as db:
        try:
            await db.execute(
                "INSERT INTO subscriptions (chat_id, twitch_login) VALUES (?, ?)",
                (chat_id, twitch_login.lower())
            )
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False

async def remove_subscription(chat_id: int, twitch_login: str):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "DELETE FROM subscriptions WHERE chat_id = ? AND twitch_login = ?",
            (chat_id, twitch_login.lower())
        )
        await db.commit()

async def get_subscriptions_by_chat(chat_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT twitch_login, custom_template FROM subscriptions WHERE chat_id = ?",
            (chat_id,)
        ) as cursor:
            return await cursor.fetchall()

async def get_all_subscriptions():
    """Returns all unique twitch logins to monitor."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT DISTINCT twitch_login FROM subscriptions") as cursor:
            rows = await cursor.fetchall()
            return [row['twitch_login'] for row in rows]

async def get_chats_for_channel(twitch_login: str):
    """Returns chats and their templates (using LEFT JOIN to get persisted templates)."""
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT s.chat_id, t.template as custom_template, s.is_live 
            FROM subscriptions s
            LEFT JOIN templates t ON s.chat_id = t.chat_id AND s.twitch_login = t.twitch_login
            WHERE s.twitch_login = ?
            """,
            (twitch_login.lower(),)
        ) as cursor:
            return await cursor.fetchall()

async def set_template(chat_id: int, twitch_login: str, template: str):
    async with aiosqlite.connect(DB_NAME) as db:
        login_lower = twitch_login.lower()
        # Используем INSERT OR REPLACE для таблицы шаблонов
        await db.execute(
            "INSERT OR REPLACE INTO templates (chat_id, twitch_login, template) VALUES (?, ?, ?)",
            (chat_id, login_lower, template)
        )
        await db.commit()
        logging.info(f"DB: Persisted template for chat_id={chat_id}, login={login_lower}")
        return True

async def get_custom_template(chat_id: int, twitch_login: str):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row
        login_lower = twitch_login.lower()
        async with db.execute(
            "SELECT template FROM templates WHERE chat_id = ? AND twitch_login = ?",
            (chat_id, login_lower)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                res = row['template']
                logging.info(f"DEBUG DB: chat_id={chat_id}, login={login_lower}, found_template={res}")
                return res
            return None

async def update_live_status(twitch_login: str, is_live: bool):
    """Updates the live status for all subscriptions of a specific channel."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE subscriptions SET is_live = ? WHERE twitch_login = ?",
            (1 if is_live else 0, twitch_login.lower())
        )
        await db.commit()
