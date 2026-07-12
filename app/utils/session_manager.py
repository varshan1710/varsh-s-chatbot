"""
Session Manager
================
Manages in-memory conversation sessions. Each session maintains a separate
message history so multiple users/contexts remain fully isolated.

This is designed to be swappable — replace the in-memory dict with a
Redis/database backend without changing any other service code.

Usage:
    from app.utils.session_manager import SessionManager

    manager = SessionManager()
    manager.add_message("user123", "user", "Hello!")
    history = manager.get_history("user123")
"""

import uuid
from datetime import datetime
from threading import Lock
from typing import Dict, List, Optional
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ConversationSession:
    """
    Represents a single conversation session.
    Stores the full message history and metadata.
    """

    def __init__(self, session_id: str, system_prompt: Optional[str] = None):
        self.session_id: str = session_id
        self.system_prompt: Optional[str] = system_prompt
        self.history: List[Dict[str, str]] = []  # [{role, content}]
        self.created_at: datetime = datetime.utcnow()
        self.last_active: datetime = datetime.utcnow()
        self.message_count: int = 0

    def add_message(self, role: str, content: str) -> None:
        """
        Append a message to the conversation history.

        Args:
            role: 'user' or 'model'
            content: The message text
        """
        self.history.append({"role": role, "parts": [{"text": content}]})
        self.message_count += 1
        self.last_active = datetime.utcnow()

    def get_history(self) -> List[Dict]:
        """Return the full conversation history."""
        return self.history

    def clear(self) -> None:
        """Reset the conversation history while keeping session metadata."""
        self.history = []
        self.message_count = 0
        logger.info(f"Session '{self.session_id}' cleared.")


class SessionManager:
    """
    Thread-safe in-memory session store.

    Manages multiple ConversationSession instances keyed by session_id.
    Designed for easy replacement with a persistent backend (Redis, DB, etc.)
    """

    def __init__(self):
        self._sessions: Dict[str, ConversationSession] = {}
        self._lock = Lock()

    def get_or_create(
        self,
        session_id: str,
        system_prompt: Optional[str] = None,
    ) -> ConversationSession:
        """
        Return an existing session or create a new one.

        Args:
            session_id: Unique identifier for the session.
            system_prompt: Optional system prompt to use when creating a new session.

        Returns:
            The ConversationSession for the given session_id.
        """
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = ConversationSession(
                    session_id=session_id,
                    system_prompt=system_prompt,
                )
                logger.info(f"New session created: '{session_id}'")
            return self._sessions[session_id]

    def clear_session(self, session_id: str) -> bool:
        """
        Clear the history of a specific session.

        Args:
            session_id: The session to clear.

        Returns:
            True if session existed and was cleared, False otherwise.
        """
        with self._lock:
            if session_id in self._sessions:
                self._sessions[session_id].clear()
                return True
            return False

    def delete_session(self, session_id: str) -> bool:
        """
        Completely remove a session from the store.

        Args:
            session_id: The session to delete.

        Returns:
            True if deleted, False if not found.
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"Session deleted: '{session_id}'")
                return True
            return False

    def list_sessions(self) -> List[str]:
        """Return all active session IDs."""
        with self._lock:
            return list(self._sessions.keys())

    def generate_session_id(self) -> str:
        """Generate a new unique session ID."""
        return str(uuid.uuid4())

    @property
    def session_count(self) -> int:
        """Number of active sessions in memory."""
        return len(self._sessions)


# Global singleton — shared across all API route handlers
session_manager = SessionManager()
