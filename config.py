import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8598099433:AAG0TlcHZbM_sqs73Mzvfkm48cynNIbW1sA")
ADMIN_ID = int(os.getenv("ADMIN_ID", "1284800175"))
DB_NAME = "bot_database.db"
