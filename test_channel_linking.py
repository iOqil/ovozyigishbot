import asyncio
import aiosqlite
from config import DB_NAME
from database import create_tables

async def test():
    # Ensure tables exist
    await create_tables()

    # Helper to clean tables
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM surveys")
        await db.execute("DELETE FROM channels")
        await db.execute("DELETE FROM survey_channels")
        await db.commit()

    # 1. Create Surveys
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("INSERT INTO surveys (title, description, is_active) VALUES (?, ?, 1)", ("Medical Survey", "Medical Desc"))
        medical_survey_id = cursor.lastrowid
        
        cursor = await db.execute("INSERT INTO surveys (title, description, is_active) VALUES (?, ?, 1)", ("Sports Survey", "Sports Desc"))
        sports_survey_id = cursor.lastrowid
        
        # 2. Create Channels
        cursor = await db.execute("INSERT INTO channels (channel_id, name, url) VALUES (?, ?, ?)", ("-1001", "Medical Channel", "http://t.me/med"))
        medical_channel_db_id = cursor.lastrowid
        
        cursor = await db.execute("INSERT INTO channels (channel_id, name, url) VALUES (?, ?, ?)", ("-1002", "Sports Channel", "http://t.me/sport"))
        sports_channel_db_id = cursor.lastrowid
        
        await db.commit()
        
        print(f"Created Medical Survey ID: {medical_survey_id}")
        print(f"Created Sports Survey ID: {sports_survey_id}")
        print(f"Created Medical Channel ID: {medical_channel_db_id}")
        print(f"Created Sports Channel ID: {sports_channel_db_id}")
        
        # 3. Link Channels
        # Medical Survey needs Medical Channel
        await db.execute("INSERT INTO survey_channels (survey_id, channel_id) VALUES (?, ?)", (medical_survey_id, medical_channel_db_id))
        
        # Sports Survey needs Sports Channel
        await db.execute("INSERT INTO survey_channels (survey_id, channel_id) VALUES (?, ?)", (sports_survey_id, sports_channel_db_id))
        
        await db.commit()
        
        # 4. Verify Logic
        print("\n--- Testing Requirements ---")
        
        async def check_required_channels(s_id):
             async with db.execute("""
                SELECT c.name
                FROM channels c
                JOIN survey_channels sc ON c.id = sc.channel_id
                WHERE sc.survey_id = ?
            """, (s_id,)) as cursor:
                 rows = await cursor.fetchall()
                 return [r[0] for r in rows]

        req_med = await check_required_channels(medical_survey_id)
        print(f"Medical Survey requires: {req_med}")
        if "Medical Channel" in req_med and "Sports Channel" not in req_med:
             print("[PASS] Medical Survey verification passed")
        else:
             print("[FAIL] Medical Survey verification FAILED")
        
        req_sport = await check_required_channels(sports_survey_id)
        print(f"Sports Survey requires: {req_sport}")
        if "Sports Channel" in req_sport and "Medical Channel" not in req_sport:
             print("[PASS] Sports Survey verification passed")
        else:
             print("[FAIL] Sports Survey verification FAILED")

        # Cleanup? 
        # Maybe keep for inspection if needed. But usually cleanup.
        # await db.execute("DELETE FROM surveys")
        # await db.execute("DELETE FROM channels")
        # await db.execute("DELETE FROM survey_channels")
        # await db.commit()

if __name__ == "__main__":
    asyncio.run(test())
