"""
GeminiChatbot — Core Reusable Chatbot Class
=============================================
This is the heart of the module. It wraps the Google GenAI SDK and exposes
a simple, stable interface that the rest of the application uses.

REUSABLE: Import this class into ANY Python project:

    from chatbot import GeminiChatbot

    bot = GeminiChatbot()
    reply = bot.chat(message="Hello!", session_id="user1")

The class hides all Gemini SDK complexity. Callers only need bot.chat().

Architecture notes:
  - Uses Dependency Injection for settings (testable, flexible)
  - Session history is delegated to SessionManager (single responsibility)
  - Streaming is supported via chat_stream()
  - All Gemini errors are caught and re-raised as plain Python exceptions

Future extensibility points (add without changing core API):
  - Image input: pass PIL.Image to contents list
  - PDF chat: extract text, inject as context
  - Function calling: add tools= parameter to generate_content
  - RAG: inject retrieved chunks into system prompt
  - Database sessions: swap SessionManager backend
"""

from typing import Optional, AsyncGenerator
from google import genai
from google.genai import types

from app.config.settings import Settings, get_settings
from app.utils.session_manager import SessionManager, session_manager as default_session_manager
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GeminiChatbot:
    """
    Production-quality, reusable AI chatbot powered by Google Gemini.

    Features:
        - Multi-session conversation history
        - Configurable system prompt / personality
        - Streaming support
        - Full error handling and logging
        - Pluggable session storage

    Example:
        >>> bot = GeminiChatbot()
        >>> reply = bot.chat("What is Python?", session_id="user-42")
        >>> print(reply)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
        settings: Optional[Settings] = None,
        session_store: Optional[SessionManager] = None,
    ):
        """
        Initialize the GeminiChatbot.

        Args:
            api_key: Gemini API key. Falls back to GEMINI_API_KEY env var.
            model: Gemini model name. Falls back to MODEL env var.
            system_prompt: Default system prompt. Falls back to SYSTEM_PROMPT env var.
            settings: Injected Settings object (for testing/DI). Auto-loaded if None.
            session_store: Injected SessionManager (for testing/DI). Uses global if None.
        """
        self._settings = settings or get_settings()
        self._session_manager = session_store or default_session_manager

        # Allow constructor overrides for standalone / library use
        self._api_key = api_key or self._settings.GEMINI_API_KEY
        self._model = model or self._settings.MODEL
        self._default_system_prompt = system_prompt or self._settings.SYSTEM_PROMPT

        # Validate API key is present
        if not self._api_key:
            raise ValueError(
                "No Gemini API key provided. "
                "Pass api_key=... or set GEMINI_API_KEY in your .env file."
            )

        # Initialize Gemini client
        self._client = genai.Client(api_key=self._api_key)

        logger.info(
            f"GeminiChatbot initialized | model={self._model} | "
            f"system_prompt_length={len(self._default_system_prompt)}"
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Public API
    # ─────────────────────────────────────────────────────────────────────────

    def chat(
        self,
        message: str,
        session_id: str = "default",
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Send a message and get a complete text response.

        This is the primary integration point for plug-and-play usage.
        All Gemini SDK details are hidden — callers only call this method.

        Args:
            message: The user's input message.
            session_id: Unique identifier for this conversation thread.
                        Different session IDs maintain separate histories.
            system_prompt: Override the default system prompt for this call.
                           Useful for per-user personality customization.

        Returns:
            The AI assistant's response as a plain string.

        Raises:
            RuntimeError: If the Gemini API call fails.

        Example:
            >>> bot = GeminiChatbot()
            >>> reply = bot.chat("Hello!", session_id="user-1")
            >>> print(reply)  # "Hi there! How can I help you today?"
        """
        active_system_prompt = system_prompt or self._default_system_prompt

        # Get or create the session (preserves conversation history)
        session = self._session_manager.get_or_create(
            session_id=session_id,
            system_prompt=active_system_prompt,
        )

        # Append the user message to history
        session.add_message(role="user", content=message)

        logger.info(
            f"Chat | session='{session_id}' | "
            f"msg_count={session.message_count} | "
            f"user_msg='{message[:80]}{'...' if len(message) > 80 else ''}'"
        )

        try:
            # Build generation config from settings
            config = types.GenerateContentConfig(
                system_instruction=active_system_prompt,
                temperature=self._settings.TEMPERATURE,
                max_output_tokens=self._settings.MAX_OUTPUT_TOKENS,
            )

            # Send full conversation history to preserve context
            response = self._client.models.generate_content(
                model=self._model,
                contents=session.get_history(),
                config=config,
            )

            reply_text = response.text

            # Append the assistant's response to history
            session.add_message(role="model", content=reply_text)

            logger.info(
                f"Reply | session='{session_id}' | "
                f"reply_length={len(reply_text)} chars"
            )

            return reply_text

        except Exception as exc:
            # Remove the user's message from history on failure to keep history clean
            session.history.pop()
            session.message_count -= 1

            logger.error(f"Gemini API error | session='{session_id}' | error={exc}")
            raise RuntimeError(f"Failed to get response from Gemini: {exc}") from exc

    async def chat_stream(
        self,
        message: str,
        session_id: str = "default",
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Send a message and stream the response token by token.

        Args:
            message: The user's input message.
            session_id: Conversation session identifier.
            system_prompt: Optional system prompt override.

        Yields:
            Text chunks as they arrive from the Gemini API.

        Example:
            >>> async for chunk in bot.chat_stream("Tell me a story"):
            ...     print(chunk, end="", flush=True)
        """
        active_system_prompt = system_prompt or self._default_system_prompt
        session = self._session_manager.get_or_create(
            session_id=session_id,
            system_prompt=active_system_prompt,
        )
        session.add_message(role="user", content=message)

        config = types.GenerateContentConfig(
            system_instruction=active_system_prompt,
            temperature=self._settings.TEMPERATURE,
            max_output_tokens=self._settings.MAX_OUTPUT_TOKENS,
        )

        full_reply = ""

        try:
            for chunk in self._client.models.generate_content_stream(
                model=self._model,
                contents=session.get_history(),
                config=config,
            ):
                if chunk.text:
                    full_reply += chunk.text
                    yield chunk.text

            # Only persist to history after complete response
            session.add_message(role="model", content=full_reply)

        except Exception as exc:
            session.history.pop()
            session.message_count -= 1
            logger.error(f"Stream error | session='{session_id}' | error={exc}")
            raise RuntimeError(f"Streaming failed: {exc}") from exc

    def new_session(self, session_id: str) -> bool:
        """
        Clear a session's conversation history (start fresh).

        Args:
            session_id: The session to reset.

        Returns:
            True if the session existed and was cleared.
        """
        result = self._session_manager.clear_session(session_id)
        logger.info(f"Session reset: '{session_id}' | found={result}")
        return result

    def get_available_models(self) -> list[dict]:
        """
        Return a list of supported Gemini models with descriptions.
        Extend this list as Google releases new models.

        Returns:
            List of dicts with 'name' and 'description' keys.
        """
        return [
            {
                "name": "gemini-2.5-flash",
                "description": "Latest Flash model — fastest, most cost-effective",
            },
            {
                "name": "gemini-2.5-pro",
                "description": "Most capable model for complex reasoning tasks",
            },
            {
                "name": "gemini-2.0-flash",
                "description": "Previous generation Flash — stable and reliable",
            },
            {
                "name": "gemini-1.5-pro",
                "description": "Long context window, great for document analysis",
            },
            {
                "name": "gemini-1.5-flash",
                "description": "Balanced speed and capability",
            },
        ]

    @property
    def current_model(self) -> str:
        """The currently active Gemini model name."""
        return self._model

    @property
    def session_count(self) -> int:
        """Number of active conversation sessions."""
        return self._session_manager.session_count
