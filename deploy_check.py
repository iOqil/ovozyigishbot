import os
import sys
import logging

def check_env():
    print("--- Environment Check ---")
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    
    dot_env_exists = os.path.exists(".env")
    print(f".env file exists: {dot_env_exists}")
    
    from config import BOT_TOKEN, ADMIN_ID
    if BOT_TOKEN == "8598099433:AAG0TlcHZbM_sqs73Mzvfkm48cynNIbW1sA":
        print("WARNING: Using default BOT_TOKEN from config.py. Make sure this is intended.")
    else:
        print("SUCCESS: Custom BOT_TOKEN detected.")
        
    print(f"Admin ID: {ADMIN_ID}")

async def check_db():
    print("\n--- Database Check ---")
    try:
        from database import create_tables
        import asyncio
        await create_tables()
        print("SUCCESS: Database connection and table creation successful.")
    except Exception as e:
        print(f"ERROR: Database check failed: {e}")

if __name__ == "__main__":
    check_env()
    try:
        import asyncio
        asyncio.run(check_db())
    except ImportError:
        print("ERROR: asyncio or other dependencies missing.")
    except Exception as e:
        print(f"ERROR: An unexpected error occurred: {e}")
