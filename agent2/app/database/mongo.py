"""
app/database/mongo.py

MongoDB connectivity for the Fraud Intelligence Platform.
Responsible ONLY for connecting and exposing client, db, and get_collection().
"""

from loguru import logger
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConfigurationError, ConnectionFailure, ServerSelectionTimeoutError

from app.config.constants import VALID_COLLECTIONS
from app.config.settings import settings


def _connect() -> MongoClient:
    """Create a MongoClient and verify the connection with a ping."""
    if not settings.MONGO_URI:
        raise ValueError("MONGO_URI is not set. Add it to your .env file.")

    try:
        mongo_client: MongoClient = MongoClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=5000,
        )
        mongo_client.admin.command("ping")
        logger.success("MongoDB connected — database: '{}'", settings.DATABASE_NAME)
        return mongo_client

    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        logger.error("MongoDB connection failed: {}", e)
        raise

    except ConfigurationError as e:
        logger.error("MongoDB configuration error: {}", e)
        raise


client: MongoClient = _connect()
db: Database = client[settings.DATABASE_NAME]
logger.info(
    "Using MongoDB database '{}'",
    settings.DATABASE_NAME,
)


def get_collection(name: str) -> Collection:
    """
    Return a collection handle by name.

    Raises ValueError if the name is not in VALID_COLLECTIONS.
    """
    if name not in VALID_COLLECTIONS:
        raise ValueError(
            f"Unknown collection '{name}'. "
            f"Expected one of: {', '.join(sorted(VALID_COLLECTIONS))}"
        )
    return db[name]
