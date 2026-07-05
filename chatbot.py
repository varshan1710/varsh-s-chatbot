"""
GeminiChatbot — Public Module Interface
=========================================
Import this module to use GeminiChatbot as a reusable component
in any Python project.

Quickstart:
    from chatbot import GeminiChatbot

    bot = GeminiChatbot()  # reads GEMINI_API_KEY from .env

    reply = bot.chat(
        message="Hello, what can you do?",
        session_id="my-user-id"
    )
    print(reply)

Or with an explicit API key (not recommended — use .env instead):
    bot = GeminiChatbot(api_key="your-key-here")
"""

from app.services.chatbot_service import GeminiChatbot

__all__ = ["GeminiChatbot"]
__version__ = "1.0.0"
__author__ = "GeminiChatbot Module"
