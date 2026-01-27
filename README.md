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

3.  **Botni ishga tushirish:**
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
    *   `/channels` - Kanallarni boshqarish (qo'shish/o'chirish).
    *   `/survey_channels` - So'rovnomaga majburiy kanallarni biriktirish.
    *   `/post_survey` - So'rovnomani kanalga joylash.
    *   `/phone_numbers` - Ro'yxatdan o'tganlar ro'yxatini (.txt) yuklab olish.
    *   Rasm yuklash, tavsif yozish va nomzodlarni qo'shish imkoniyati.

## Ma'lumotlar bazasi
*   Barcha ma'lumotlar `bot_database.db` faylida saqlanadi (SQLite).
*   Dastlabki "Samarqand" so'rovnomasi avtomatik yaratilgan.

## Admin ID
Hozirgi Admin ID: `1284800175`. O'zgartirish uchun `config.py` faylini tahrirlang.

## Docker'da Ishga tushirish

### Talablar:
- Docker o'rnatilgan bo'lishi kerak
- Docker Compose o'rnatilgan bo'lishi kerak

### Qadamlar:

1. **Environment faylini tayyorlash:**
   `.env.example` faylini `.env` sifatida nusxala va majburiy qiymatlarni kiriting:
   ```bash
   cp .env.example .env
   ```

2. **Docker kontejnerini ishga tushirish:**
   ```bash
   docker-compose up -d
   ```

3. **Kontejnerning holatini tekshirish:**
   ```bash
   docker-compose ps
   ```

4. **Jurnallarni ko'rish:**
   ```bash
   docker-compose logs -f bot
   ```

5. **Kontejnerga kirish (agar kerak bo'lsa):**
   ```bash
   docker-compose exec bot bash
   ```

6. **Kontejnerini to'xtatish:**
   ```bash
   docker-compose down
   ```

### Docker Qo'llanmasi:

- **Kontejnerini qayta ishga tushirish:**
  ```bash
  docker-compose restart bot
  ```

- **Tahrirlash uchun qayta qurilish:**
  ```bash
  docker-compose up --build
  ```

- **Volume'larni tozalash:**
  ```bash
  docker-compose down -v
  ```
