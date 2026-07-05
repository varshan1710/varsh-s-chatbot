"""
FastAPI Application Factory
=============================
Creates and configures the FastAPI application instance.
Registers all routers, middleware, CORS, and exception handlers.
Static file serving for the frontend HTML/CSS/JS.
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

# ─────────────────────────────────────────────
# Create FastAPI app
# ─────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "A production-quality, reusable AI chatbot module powered by Google Gemini. "
        "Supports multi-session conversations, streaming, and plug-and-play integration."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={
        "name": "GeminiChatbot API",
        "url": "http://localhost:8000/docs",
    },
)

# ─────────────────────────────────────────────
# CORS Middleware
# Allow the frontend (running on same origin or localhost) to call the API
# ─────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # Restrict to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
# Mount static files (frontend)
# ─────────────────────────────────────────────

app.mount("/static", StaticFiles(directory="frontend/static"), name="static")

# ─────────────────────────────────────────────
# Register API router
# ─────────────────────────────────────────────

app.include_router(router)

# ─────────────────────────────────────────────
# Global exception handler
# ─────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler to return clean JSON errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# ─────────────────────────────────────────────
# Serve frontend
# ─────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def serve_frontend():
    """Serve the main chat UI."""
    return FileResponse("frontend/index.html")


# ─────────────────────────────────────────────
# Startup / shutdown events
# ─────────────────────────────────────────────

from app.config.database import close_client

@app.on_event("startup")
async def on_startup():
    logger.info(f"✅ {settings.APP_NAME} is ready!")
    logger.info(f"   Model: {settings.MODEL}")
    logger.info(f"   Docs:  http://localhost:8000/docs")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info(f"🛑 {settings.APP_NAME} shutting down...")
    await close_client()

