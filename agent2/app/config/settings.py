import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # App
    APP_NAME = os.getenv("APP_NAME", "Agent 2")

    # MongoDB
    MONGO_URI = os.getenv("MONGO_URI")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "fraud_intelligence")

    # Reddit
    REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
    REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
    REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT")

    # Telegram
    TELEGRAM_API_ID = int(os.getenv("TELEGRAM_API_ID", 0))
    TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")

    # Groq
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")


settings = Settings()