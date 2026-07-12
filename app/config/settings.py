"""
Application Settings
======================
Loads and validates configuration from the .env file using Pydantic Settings.
All environment variables are type-checked and validated at startup.
Credentials are stored as hashed values — raw secrets never appear in code.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # === Gemini API ===
    GEMINI_API_KEY: str = Field(..., description="Google Gemini API Key")
    MODEL: str = Field(default="gemini-2.5-flash", description="Gemini model to use")
    TEMPERATURE: float = Field(default=0.7, ge=0.0, le=2.0, description="Generation temperature")
    MAX_OUTPUT_TOKENS: int = Field(default=2048, gt=0, description="Max tokens in response")

    # === System Prompt ===
    SYSTEM_PROMPT: str = Field(
        default="You are a helpful, friendly, and intelligent AI assistant.",
        description="Default system prompt for the chatbot personality",
    )

    # === App Config ===
    APP_NAME: str = Field(default="Varsh's Personal AI", description="Application name")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # === Authentication (values loaded from .env — never hardcoded) ===
    AUTH_USER_ID: str = Field(..., description="Authorized user identifier (from .env)")
    AUTH_PASSWORD_HASH: str = Field(..., description="Bcrypt hash of the authorized password (from .env)")
    JWT_SECRET: str = Field(..., description="Secret key for signing JWT tokens")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT signing algorithm")
    JWT_EXPIRE_HOURS: int = Field(default=8, description="JWT token lifetime in hours")

    # === MongoDB ===
    MONGODB_URL: str = Field(default="mongodb://localhost:27017", description="MongoDB connection URI")
    MONGODB_DB: str = Field(default="vp_ai_db", description="MongoDB database name")


@lru_cache()
def get_settings() -> Settings:
    """
    Return a cached singleton of the application settings.
    Uses lru_cache to avoid re-reading the .env file on every call.
    """
    return Settings()
