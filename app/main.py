"""
Main FastAPI Application Entry Point for FitBuddy.
Initializes the app, middleware, database, static files, and exception handlers.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.database import init_db
from app.routes import router as app_router
from app.utils import FITNESS_SAFETY_DISCLAIMER

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("fitbuddy.main")

# Directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Ensure directories exist
STATIC_DIR.mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "css").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "js").mkdir(parents=True, exist_ok=True)
(STATIC_DIR / "images").mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan context manager.
    Runs database schema initialization on startup.
    """
    logger.info("Initializing FitBuddy SQLite database tables...")
    init_db()
    logger.info("FitBuddy database initialization complete.")
    yield
    logger.info("FitBuddy application shutting down.")


app = FastAPI(
    title="FitBuddy – AI Fitness Plan Generator",
    description=(
        "Production-grade AI Fitness Plan Generator powered by Google Gemini and FastAPI. "
        "Generates customized 7-day workout routines, evidence-based nutrition tips, and supports "
        "feedback-driven routine updates with persistent plan history."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add Starlette Session Middleware for Admin authentication
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="fitbuddy_session",
    max_age=86400,  # 24 hours
    same_site="lax",
    https_only=settings.is_production
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Include routes
app.include_router(app_router)


# ==============================================================================
# GLOBAL EXCEPTION HANDLERS
# ==============================================================================

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handles HTTP exceptions cleanly for both web browser and API requests."""
    # Check if request accepts HTML or is calling an API endpoint
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "detail": exc.detail}
        )

    if exc.status_code == 404:
        return templates.TemplateResponse(
            request=request,
            name="404.html",
            context={"message": exc.detail or "The requested page was not found."},
            status_code=status.HTTP_404_NOT_FOUND
        )

    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "title": f"Error {exc.status_code}",
            "message": exc.detail or "An error occurred while processing your request.",
            "return_url": "/"
        },
        status_code=exc.status_code
    )


@app.exception_handler(Exception)
async def global_unhandled_exception_handler(request: Request, exc: Exception):
    """Catches all unhandled server exceptions and returns friendly user views."""
    logger.exception(f"Unhandled server error: {exc}")

    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "detail": "An unexpected server error occurred."}
        )

    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "title": "Internal Server Error",
            "message": "FitBuddy encountered an unexpected situation. Please try again in a few moments.",
            "return_url": "/"
        },
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
