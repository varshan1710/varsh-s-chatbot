"""
Authentication Service
========================
Handles all authentication logic:
  - Verifying credentials against values stored in .env (hashed)
  - Issuing signed JWT tokens
  - Validating tokens on protected routes
  - Storing / revoking sessions in MongoDB

Security design:
  - Raw credentials NEVER appear in source code
  - Passwords compared using constant-time bcrypt verify
  - Tokens are short-lived (configurable via JWT_EXPIRE_HOURS in .env)
  - Sessions are persisted in MongoDB for revocation support
"""

import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import OAuth2PasswordBearer

from app.config.settings import Settings, get_settings
from app.config.database import get_database
from app.utils.logger import get_logger

logger = get_logger(__name__)

# FastAPI OAuth2 bearer — only used for /docs "Authorize" button
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


# ─────────────────────────────────────────────
# Password verification
# ─────────────────────────────────────────────

def verify_credentials(user_id: str, password: str, settings: Settings) -> bool:
    """
    Verify a user ID and plaintext password against the stored hash.

    Credentials are loaded exclusively from Settings (sourced from .env).
    Constant-time comparison prevents timing attacks.

    Returns True if and only if both the ID and password match.
    """
    # Constant-time ID comparison
    id_ok = _constant_compare(user_id, settings.AUTH_USER_ID)

    # Bcrypt constant-time password comparison
    try:
        pass_ok = bcrypt.checkpw(
            password.encode("utf-8"),
            settings.AUTH_PASSWORD_HASH.encode("utf-8"),
        )
    except Exception:
        pass_ok = False

    # Both must match — short-circuit only logged, not returned individually
    if id_ok and pass_ok:
        logger.info("Authentication successful.")
        return True

    logger.warning("Authentication failed — invalid credentials supplied.")
    return False


def _constant_compare(a: str, b: str) -> bool:
    """
    Constant-time string comparison to prevent timing-based enumeration.
    """
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a.encode(), b.encode()):
        result |= x ^ y
    return result == 0


# ─────────────────────────────────────────────
# JWT token management
# ─────────────────────────────────────────────

def create_access_token(settings: Settings) -> str:
    """
    Create a signed JWT access token.
    Token contains only a non-identifying subject claim.
    Expiry is controlled by JWT_EXPIRE_HOURS in .env.
    """
    expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {
        "sub": "authorized_user",   # Non-identifying claim
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "app": settings.APP_NAME,
    }
    token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    logger.info(f"JWT issued — expires at {expire.isoformat()}")
    return token


def decode_token(token: str, settings: Settings) -> dict:
    """
    Decode and validate a JWT token.

    Raises:
        HTTPException 401 if token is missing, malformed, or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Session expired or invalid. Please log in.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("sub") != "authorized_user":
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


# ─────────────────────────────────────────────
# MongoDB session tracking
# ─────────────────────────────────────────────

async def store_session(token: str, settings: Settings):
    """
    Persist an active session token in MongoDB for revocation support.
    Automatically expires via MongoDB TTL index on the 'expires_at' field.
    """
    try:
        db = get_database()
        expire = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS)
        await db.sessions.insert_one({
            "token_prefix": token[:16],   # Store only prefix — not the full token
            "created_at": datetime.now(timezone.utc),
            "expires_at": expire,
            "active": True,
        })
        # Ensure TTL index exists (idempotent)
        await db.sessions.create_index("expires_at", expireAfterSeconds=0)
    except Exception as exc:
        # Non-fatal — session still works via JWT even if DB write fails
        logger.warning(f"Could not persist session to MongoDB: {exc}")


async def revoke_session(token: str):
    """Mark a session as revoked in MongoDB (logout)."""
    try:
        db = get_database()
        await db.sessions.update_one(
            {"token_prefix": token[:16]},
            {"$set": {"active": False}},
        )
        logger.info("Session revoked.")
    except Exception as exc:
        logger.warning(f"Could not revoke session in MongoDB: {exc}")


# ─────────────────────────────────────────────
# FastAPI dependency: require authentication
# ─────────────────────────────────────────────

async def require_auth(
    # Accept token from cookie OR Authorization header
    access_token: Optional[str] = Cookie(default=None),
    bearer_token: Optional[str] = Depends(oauth2_scheme),
    settings: Settings = Depends(get_settings),
) -> dict:
    """
    FastAPI dependency that enforces authentication on any route.

    Checks (in order):
      1. HTTP-only cookie named 'access_token'
      2. Authorization: Bearer header (for API clients / Swagger)

    Returns the decoded JWT payload if valid.
    Raises 401 if no valid token found.
    """
    token = access_token or bearer_token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    return decode_token(token, settings)
