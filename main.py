import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import create_tables
from handlers import user, admin

async def main():
    logging.basicConfig(level=logging.INFO)
    
    # Initialize DB
    await create_tables()
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Register routers (we'll implement these next)
    dp.include_router(user.router)
    dp.include_router(admin.router)

    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
