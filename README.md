# Telegram Survey Bot

Ushbu bot Telegram orqali so'rovnomalar o'tkazish, ovoz berish va admin panel orqali boshqarish uchun mo'ljallangan.

## Texnologiyalar
- **Python 3.11+**
- **Aiogram 3.x**
- **SQLite** (axborotlar bazasi sifatida)
- **Docker** & **Docker Compose**

## O'rnatish va Ishga tushirish

### 1. Lokal ishga tushirish
1. Loyihani yuklab oling.
2. `.env.example` faylidan nusxa olib, `.env` faylini yarating va o'z ma'lumotlaringizni kiriting:
   ```bash
   cp .env.example .env
   ```
3. Kutubxonalarni o'rnating:
   ```bash
   pip install -r requirements.txt
   ```
4. Botni ishga tushiring:
   ```bash
   python main.py
   ```

### 2. Docker orqali ishga tushirish
1. Docker va Docker Compose o'rnatilganligiga ishonch hosil qiling.
2. `.env` faylini sozlang.
3. Konteynerni build qiling va ishga tushiring:
   ```bash
   docker-compose up -d --build
   ```

## Xususiyatlari
*   **Foydalanuvchi:**
    *   `/start` - Botni ishga tushirish.
    *   "🗳 Ovoz berish" tugmasi orqali so'rovnomalarni ko'rish.
    *   Nomzodlarga ovoz berish (bir kishi bir marta).
*   **Admin:**
    *   `/admin` - Admin panelga kirish.
    *   `/create_survey` - Yangi so'rovnoma yaratish.
    *   `/channels` - Kanallarni boshqarish.
    *   `/survey_channels` - So'rovnomaga majburiy kanallarni biriktirish.
    *   `/post_survey` - So'rovnomani kanalga joylash.
    *   `/phone_numbers` - Ro'yxatdan o'tganlar ro'yxatini yuklab olish.

## Xavfsizlik
Loyihani GitHub'ga yuklashdan oldin `.env` fayli `.gitignore`da ekanligiga ishonch hosil qiling. Hech qachon maxfiy tokenlarni kodning o'zida qoldirmang. `config.py` fayli faqat muhit o'zgaruvchilari bilan ishlashga sozlangan.
