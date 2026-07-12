"""
MongoDB Client
===============
Provides a shared async Motor (MongoDB) client for the application.
Handles connection lifecycle and exposes the session collection.

Collections used:
  - sessions: active JWT sessions with expiry
"""

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    """Return the shared MongoDB client (created on first call)."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncIOMotorClient(settings.MONGODB_URL, serverSelectionTimeoutMS=3000)
        logger.info(f"MongoDB client initialized → {settings.MONGODB_URL}")
    return _client


def get_database() -> AsyncIOMotorDatabase:
    """Return the application database."""
    settings = get_settings()
    return get_client()[settings.MONGODB_DB]


async def close_client():
    """Gracefully close the MongoDB connection on shutdown."""
    global _client
    if _client:
        _client.close()
        _client = None
        logger.info("MongoDB connection closed.")


async def ping():
    """Check MongoDB connectivity. Returns True if reachable."""
    try:
        await get_client().admin.command("ping")
        return True
    except Exception as exc:
        logger.warning(f"MongoDB ping failed: {exc}")
        return False
