import aiosqlite
import logging
from config import DB_NAME

logger = logging.getLogger(__name__)

async def get_db():
    conn = await aiosqlite.connect(DB_NAME)
    conn.row_factory = aiosqlite.Row
    return conn

async def create_tables():
    async with await get_db() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS surveys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                description TEXT,
                image_file_id TEXT,
                is_active BOOLEAN DEFAULT 1,
                is_closed BOOLEAN DEFAULT 0,
                deadline TEXT
            )
        """)
        
        # Migration for existing tables
        try:
            await db.execute("ALTER TABLE surveys ADD COLUMN is_closed BOOLEAN DEFAULT 0")
        except Exception:
            pass
            
        await db.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                survey_id INTEGER,
                full_name TEXT,
                votes_count INTEGER DEFAULT 0,
                FOREIGN KEY(survey_id) REFERENCES surveys(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                user_id INTEGER,
                survey_id INTEGER,
                candidate_id INTEGER,
                PRIMARY KEY (user_id, survey_id),
                FOREIGN KEY(survey_id) REFERENCES surveys(id),
                FOREIGN KEY(candidate_id) REFERENCES candidates(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT NOT NULL,
                name TEXT,
                url TEXT
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS survey_channels (
                survey_id INTEGER,
                channel_id INTEGER,
                PRIMARY KEY (survey_id, channel_id),
                FOREIGN KEY(survey_id) REFERENCES surveys(id),
                FOREIGN KEY(channel_id) REFERENCES channels(id)
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                phone_number TEXT,
                username TEXT,
                full_name TEXT,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

# --- User Queries ---

async def get_user_by_id(user_id: int):
    async with await get_db() as db:
        async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
            return await cursor.fetchone()

async def add_or_update_user(user_id: int, phone: str, username: str, full_name: str):
    async with await get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, phone_number, username, full_name) VALUES (?, ?, ?, ?)",
            (user_id, phone, username, full_name)
        )
        await db.commit()

async def get_active_surveys():
    async with await get_db() as db:
        async with db.execute("SELECT id, title, is_closed FROM surveys WHERE is_active = 1") as cursor:
            return await cursor.fetchall()

async def get_survey_details(survey_id: int):
    async with await get_db() as db:
        async with db.execute(
            "SELECT title, description, image_file_id, is_closed FROM surveys WHERE id = ?", 
            (survey_id,)
        ) as cursor:
            return await cursor.fetchone()

async def get_survey_candidates(survey_id: int):
    async with await get_db() as db:
        async with db.execute(
            "SELECT id, full_name, votes_count FROM candidates WHERE survey_id = ? ORDER BY votes_count DESC", 
            (survey_id,)
        ) as cursor:
            return await cursor.fetchall()

async def has_user_voted(user_id: int, survey_id: int):
    async with await get_db() as db:
        async with db.execute(
            "SELECT 1 FROM votes WHERE user_id = ? AND survey_id = ?", 
            (user_id, survey_id)
        ) as cursor:
            return await cursor.fetchone() is not None

async def register_vote(user_id: int, survey_id: int, candidate_id: int):
    async with await get_db() as db:
        try:
            await db.execute(
                "INSERT INTO votes (user_id, survey_id, candidate_id) VALUES (?, ?, ?)", 
                (user_id, survey_id, candidate_id)
            )
            await db.execute(
                "UPDATE candidates SET votes_count = votes_count + 1 WHERE id = ?", 
                (candidate_id,)
            )
            await db.commit()
            return True
        except Exception as e:
            logger.error(f"Error registering vote: {e}")
            await db.rollback()
            return False

async def get_linked_channels(survey_id: int):
    async with await get_db() as db:
        async with db.execute("""
            SELECT c.channel_id, c.name, c.url 
            FROM channels c
            JOIN survey_channels sc ON c.id = sc.channel_id
            WHERE sc.survey_id = ?
        """, (survey_id,)) as cursor:
            return await cursor.fetchall()

# --- Admin Queries ---

async def delete_survey(survey_id: int):
    async with await get_db() as db:
        await db.execute("UPDATE surveys SET is_active = 0 WHERE id = ?", (survey_id,))
        await db.commit()

async def get_all_channels():
    async with await get_db() as db:
        async with db.execute("SELECT id, name, url, channel_id FROM channels") as cursor:
            return await cursor.fetchall()

async def add_channel(channel_id: str, name: str, url: str):
    async with await get_db() as db:
        await db.execute(
            "INSERT INTO channels (channel_id, name, url) VALUES (?, ?, ?)", 
            (channel_id, name, url)
        )
        await db.commit()

async def channel_exists(channel_id: str):
    async with await get_db() as db:
        async with db.execute("SELECT 1 FROM channels WHERE channel_id = ?", (str(channel_id),)) as cursor:
            return await cursor.fetchone() is not None

async def delete_channel(c_id: int):
    async with await get_db() as db:
        await db.execute("DELETE FROM channels WHERE id = ?", (c_id,))
        await db.commit()

async def close_survey(survey_id: int):
    async with await get_db() as db:
        await db.execute("UPDATE surveys SET is_closed = 1 WHERE id = ?", (survey_id,))
        await db.commit()

async def create_survey(title, description, image_file_id, deadline="2026-12-31"):
    async with await get_db() as db:
        cursor = await db.execute(
            "INSERT INTO surveys (title, description, image_file_id, is_active, deadline) VALUES (?, ?, ?, 1, ?)",
            (title, description, image_file_id, deadline)
        )
        survey_id = cursor.lastrowid
        await db.commit()
        return survey_id

async def add_candidate(survey_id: int, full_name: str):
    async with await get_db() as db:
        await db.execute("INSERT INTO candidates (survey_id, full_name) VALUES (?, ?)", (survey_id, full_name))
        await db.commit()

async def toggle_survey_channel(survey_id: int, channel_id: int):
    async with await get_db() as db:
        async with db.execute(
            "SELECT 1 FROM survey_channels WHERE survey_id = ? AND channel_id = ?", 
            (survey_id, channel_id)
        ) as cursor:
            exists = await cursor.fetchone()
            
        if exists:
            await db.execute(
                "DELETE FROM survey_channels WHERE survey_id = ? AND channel_id = ?", 
                (survey_id, channel_id)
            )
            action = "removed"
        else:
            await db.execute(
                "INSERT INTO survey_channels (survey_id, channel_id) VALUES (?, ?)", 
                (survey_id, channel_id)
            )
            action = "added"
        await db.commit()
        return action

async def get_survey_linked_channel_ids(survey_id: int):
    async with await get_db() as db:
        async with db.execute(
            "SELECT channel_id FROM survey_channels WHERE survey_id = ?", 
            (survey_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return {row['channel_id'] for row in rows}

async def get_survey_participants_report(survey_id: int):
    async with await get_db() as db:
        query = """
            SELECT 
                u.phone_number, 
                u.full_name, 
                c.full_name as candidate_name
            FROM users u
            LEFT JOIN votes v ON u.user_id = v.user_id AND v.survey_id = ?
            LEFT JOIN candidates c ON v.candidate_id = c.id
            ORDER BY 
                CASE WHEN v.candidate_id IS NULL THEN 1 ELSE 0 END,
                v.candidate_id ASC,
                u.full_name ASC
        """
        async with db.execute(query, (survey_id,)) as cursor:
            return await cursor.fetchall()
