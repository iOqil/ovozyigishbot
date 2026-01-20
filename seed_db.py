import asyncio
import aiosqlite
from config import DB_NAME
from database import create_tables

async def seed():
    await create_tables()
    
    async with aiosqlite.connect(DB_NAME) as db:
        # Check if survey exists
        async with db.execute("SELECT id FROM surveys WHERE title LIKE 'Samarqand%'") as cursor:
            if await cursor.fetchone():
                print("Survey already exists.")
                return

        print("Creating survey...")
        title = "Samarqand viloyatidagi sport muassasalari rahbarlarining qaysi biri o'tgan 2025-yilda namunali faoliyat olib bordi?"
        description = """Viloyatimizdagi qaysi sport muassasasi rahbari aholi va yoshlarning sport bilan shug'ullanishi uchun yaqindan ko'makdosh bo'ldi? 2025-yilda yuksak natijalarni qo‘lga kiritib, soha rivojiga hissa qo'shdi? Tashkilotida o‘zgarish qilib, natija ko‘rsatdi?

Fidoyi, xalqqa yaqin, munosib rahbarni — Sizning e’tirofingiz aniqlab beradi. So‘rovnomada eng ko‘p ovoz to‘plagan sport muassasasi munosib rag‘batlantiriladi.

Tanlov shu yilning 25-yanvar kuni 21:00 da yakunlanadi.

«Yilning eng namunali sport muassasasi rahbari»ga ovoz bering! Sizning fikringiz biz uchun muhim!"""
        
        # Insert survey
        cursor = await db.execute(
            "INSERT INTO surveys (title, description, image_file_id, is_active, deadline) VALUES (?, ?, ?, 1, ?)",
            (title, description, None, "2025-01-25 21:00")
        )
        survey_id = cursor.lastrowid
        
        # Insert dummy candidates
        candidates = [
            "Aliyev Vali (Samarqand shahar sport maktabi)",
            "Valiyev G'ani (Pastdarg'om tuman BO'SM)",
            "G'aniyev Eshmat (Jomboy tuman sport bo'limi)",
            "Toshmatov Toshmat (Urgut tumani)",
            "Eshmatov Eshmat (Toyloq tumani)"
        ]
        
        for name in candidates:
            await db.execute("INSERT INTO candidates (survey_id, full_name) VALUES (?, ?)", (survey_id, name))
            
        await db.commit()
        print(f"Survey created with ID: {survey_id}")

if __name__ == "__main__":
    asyncio.run(seed())
