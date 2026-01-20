import aiosqlite
from config import DB_NAME

async def create_tables():
    async with aiosqlite.connect(DB_NAME) as db:
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
        
        # Migration for existing tables (safe to run every time)
        try:
            await db.execute("ALTER TABLE surveys ADD COLUMN is_closed BOOLEAN DEFAULT 0")
        except Exception:
            pass # Column likely exists
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
        await db.commit()
