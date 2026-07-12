"""
Chatbot Application Entry Point
================================
Run this file to start the GeminiChatbot application.

Usage:
    python main.py

The server will start on http://localhost:8000
API docs available at http://localhost:8000/docs
"""

import uvicorn
import logging
from app.config.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """Start the FastAPI application server."""
    settings = get_settings()

    logger.info(f"Starting {settings.APP_NAME}...")
    logger.info(f"Model: {settings.MODEL}")
    logger.info(f"Server running at http://localhost:8000")
    logger.info(f"API Documentation: http://localhost:8000/docs")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()
