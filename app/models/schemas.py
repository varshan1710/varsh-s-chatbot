"""
Pydantic Data Models
======================
Request and response schemas for the chatbot API.
All models use strict typing and include example values for OpenAPI docs.
"""

from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


# ─────────────────────────────────────────────
# Request Models
# ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Request body for POST /chat"""

    message: str = Field(
        ...,
        min_length=1,
        max_length=32000,
        description="The user's message to send to the chatbot",
        examples=["Hello! Can you help me with Python?"],
    )
    session_id: str = Field(
        default="default",
        description="Unique session identifier to maintain conversation history",
        examples=["user-abc123"],
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="Override the default system prompt for this session",
        examples=["You are a Python expert. Keep answers concise."],
    )
    stream: bool = Field(
        default=False,
        description="Whether to stream the response token by token",
    )


class NewChatRequest(BaseModel):
    """Request body for POST /new-chat (clears session history)"""

    session_id: str = Field(
        default="default",
        description="The session ID to reset",
        examples=["user-abc123"],
    )


# ─────────────────────────────────────────────
# Response Models
# ─────────────────────────────────────────────

class ChatResponse(BaseModel):
    """Standard chat response"""

    reply: str = Field(..., description="The AI assistant's reply")
    session_id: str = Field(..., description="The session ID used for this conversation")
    model: str = Field(..., description="The Gemini model that generated the response")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="UTC timestamp of the response")
    message_count: int = Field(..., description="Total messages in this session (user + assistant)")


class NewChatResponse(BaseModel):
    """Response for POST /new-chat"""

    message: str = Field(..., description="Confirmation message")
    session_id: str = Field(..., description="The session that was cleared")


class HealthResponse(BaseModel):
    """Response for GET /health"""

    status: str = Field(..., description="Service status: 'ok' or 'error'")
    app_name: str = Field(..., description="Application name")
    model: str = Field(..., description="Currently configured Gemini model")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ModelInfo(BaseModel):
    """Information about a single model"""

    name: str
    description: str


class ModelsResponse(BaseModel):
    """Response for GET /models"""

    available_models: List[ModelInfo]
    current_model: str


class ErrorResponse(BaseModel):
    """Standard error response"""

    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(default=None, description="Additional error details")
    session_id: Optional[str] = Field(default=None)


class LoginRequest(BaseModel):
    """Request schema for login"""
    username: str = Field(..., description="The user's ID/Username")
    password: str = Field(..., description="The user's plaintext password")


class LoginResponse(BaseModel):
    """Response schema for successful login"""
    status: str = Field(..., description="Authentication status")
    username: str = Field(..., description="The authenticated username")
    expires_in_hours: int = Field(..., description="Token lifespan")

