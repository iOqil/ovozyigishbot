# Telegram Survey Bot

## O'rnatish va Ishga tushirish

1.  **Talablar:**
    *   Python 3.10+ o'rnatilgan bo'lishi kerak.
    *   Internet aloqasi.

2.  **Kutubxonalarni o'rnatish:**
    Terminalda quyidagi buyruqni bering:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Sozlamalar:**
    *   `.env.example` faylidan nusxa oling va nomini `.env` ga o'zgartiring:
        ```bash
        cp .env.example .env
        ```
    *   `.env` faylini oching va `BOT_TOKEN` hamda `ADMIN_ID` larni o'z ma'lumotlaringiz bilan to'ldiring.

4.  **Botni ishga tushirish:**
    ```bash
    python main.py
    ```

## Xususiyatlari
*   **Foydalanuvchi:**
    *   `/start` - Botni ishga tushirish.
    *   "🗳 Ovoz berish" tugmasi orqali so'rovnomalarni ko'rish.
    *   Nomzodlarga ovoz berish (bir kishi bir marta).
*   **Admin:**
    *   `/admin` - Admin panelga kirish (faqat belgilangan admin uchun).
    *   `/create_survey` - Yangi so'rovnoma yaratish.
    *   Rasm yuklash, tavsif yozish va nomzodlarni qo'shish imkoniyati.

## Ma'lumotlar bazasi
*   Barcha ma'lumotlar `bot_database.db` faylida saqlanadi (SQLite).
*   Dastlabki "Samarqand" so'rovnomasi avtomatik yaratilgan.

## Admin ID
Hozirgi Admin ID: `1284800175`. O'zgartirish uchun `config.py` faylini tahrirlang.
