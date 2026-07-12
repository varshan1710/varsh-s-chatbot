"""
Chat API Routes
================
FastAPI router handling all chatbot endpoints.
Business logic is delegated entirely to GeminiChatbot service.

Endpoints:
    POST /chat       — Send a message, get a reply
    POST /new-chat   — Reset a session's conversation history
    GET  /health     — Health check
    GET  /models     — List available Gemini models
"""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Response, Cookie
from fastapi.responses import StreamingResponse

from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    NewChatRequest,
    NewChatResponse,
    HealthResponse,
    ModelsResponse,
    ModelInfo,
    ErrorResponse,
    LoginRequest,
    LoginResponse,
)
from app.services.chatbot_service import GeminiChatbot
from app.services.auth_service import verify_credentials, create_access_token, require_auth, revoke_session, store_session
from app.config.settings import Settings, get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Router with /api prefix (mounted in app/main.py)
router = APIRouter(prefix="/api", tags=["Chatbot"])


# ─────────────────────────────────────────────
# Dependency: Shared chatbot instance
# Using FastAPI's dependency injection so the service
# can be swapped in tests without modifying routes.
# ─────────────────────────────────────────────

_chatbot_instance: GeminiChatbot | None = None


def get_chatbot(settings: Settings = Depends(get_settings)) -> GeminiChatbot:
    """
    Dependency that returns a shared GeminiChatbot instance.
    Created once at first request, then reused (singleton via module-level var).
    """
    global _chatbot_instance
    if _chatbot_instance is None:
        _chatbot_instance = GeminiChatbot(settings=settings)
    return _chatbot_instance


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────

@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a chat message",
    description=(
        "Send a message to the AI chatbot and receive a reply. "
        "Conversation history is maintained per session_id. "
        "Set stream=true to receive a streaming response instead."
    ),
    responses={
        200: {"description": "Successful chat response"},
        500: {"model": ErrorResponse, "description": "Gemini API error"},
    },
)
async def chat(
    request: ChatRequest,
    chatbot: GeminiChatbot = Depends(get_chatbot),
    settings: Settings = Depends(get_settings),
    current_user: dict = Depends(require_auth),
):
    """
    Main chat endpoint.

    - Maintains conversation history per session_id
    - Supports optional system_prompt override per request
    - Supports streaming via stream=true
    """
    # Handle streaming mode
    if request.stream:
        async def stream_generator():
            try:
                async for chunk in chatbot.chat_stream(
                    message=request.message,
                    session_id=request.session_id,
                    system_prompt=request.system_prompt,
                ):
                    yield chunk
            except RuntimeError as exc:
                yield f"\n[ERROR] {exc}"

        return StreamingResponse(
            stream_generator(),
            media_type="text/plain",
            headers={"X-Session-ID": request.session_id},
        )

    # Standard non-streaming response
    try:
        reply = chatbot.chat(
            message=request.message,
            session_id=request.session_id,
            system_prompt=request.system_prompt,
        )
    except RuntimeError as exc:
        logger.error(f"Chat endpoint error: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    session = chatbot._session_manager.get_or_create(request.session_id)

    return ChatResponse(
        reply=reply,
        session_id=request.session_id,
        model=settings.MODEL,
        timestamp=datetime.utcnow(),
        message_count=session.message_count,
    )


@router.post(
    "/new-chat",
    response_model=NewChatResponse,
    summary="Start a new conversation",
    description="Clear the conversation history for a given session_id.",
)
async def new_chat(
    request: NewChatRequest,
    chatbot: GeminiChatbot = Depends(get_chatbot),
    current_user: dict = Depends(require_auth),
):
    """Reset a session's conversation history."""
    chatbot.new_session(request.session_id)
    return NewChatResponse(
        message=f"Conversation cleared for session '{request.session_id}'.",
        session_id=request.session_id,
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns the service status and current configuration.",
)
async def health(settings: Settings = Depends(get_settings)):
    """Health check endpoint for monitoring and uptime checks."""
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        model=settings.MODEL,
        timestamp=datetime.utcnow(),
    )


@router.get(
    "/models",
    response_model=ModelsResponse,
    summary="List available models",
    description="Returns all supported Gemini models and the currently active one.",
)
async def models(
    chatbot: GeminiChatbot = Depends(get_chatbot),
    settings: Settings = Depends(get_settings),
    current_user: dict = Depends(require_auth),
):
    """List all available Gemini models."""
    raw_models = chatbot.get_available_models()
    return ModelsResponse(
        available_models=[
            ModelInfo(name=m["name"], description=m["description"])
            for m in raw_models
        ],
        current_model=settings.MODEL,
    )


# ─────────────────────────────────────────────
# Authentication Routes
# ─────────────────────────────────────────────

@router.post(
    "/auth/login",
    response_model=LoginResponse,
    summary="Login user",
    description="Authenticate user credentials and set HttpOnly access_token cookie."
)
async def login(
    response: Response,
    request: LoginRequest,
    settings: Settings = Depends(get_settings),
):
    if not verify_credentials(request.username, request.password, settings):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password."
        )
    token = create_access_token(settings)
    await store_session(token, settings)
    
    # Set HttpOnly, Secure, SameSite cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        max_age=settings.JWT_EXPIRE_HOURS * 3600,
        expires=settings.JWT_EXPIRE_HOURS * 3600,
        samesite="lax",
        secure=False, # Set to True in production with HTTPS
    )
    
    return LoginResponse(
        status="success",
        username=request.username,
        expires_in_hours=settings.JWT_EXPIRE_HOURS,
    )


@router.post(
    "/auth/logout",
    summary="Logout user",
    description="Revoke the session in MongoDB and clear access_token cookie."
)
async def logout(
    response: Response,
    access_token: Optional[str] = Cookie(default=None),
):
    if access_token:
        await revoke_session(access_token)
    response.delete_cookie(key="access_token")
    return {"status": "success", "message": "Successfully logged out."}


@router.get(
    "/auth/session",
    summary="Check session status",
    description="Validate active user session and return authenticated state."
)
async def check_session(
    current_user: dict = Depends(require_auth)
):
    return {"authenticated": True, "user": "authorized_user"}


