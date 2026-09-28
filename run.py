"""
Launcher script for FitBuddy application.
Runs Uvicorn ASGI server with sensible development configuration.
Usage:
    python run.py
"""

import uvicorn
from app.config import settings

if __name__ == "__main__":
    print("=" * 60)
    print("Starting FitBuddy – AI Fitness Plan Generator")
    print(f"Environment: {settings.APP_ENV}")
    print(f"Database:    {settings.DATABASE_URL}")
    print(f"Gemini Key:  {'Configured' if settings.has_gemini_api_key else 'Not set (Demo mode enabled)'}")
    print("Local URL:   http://127.0.0.1:8000")
    print("API Docs:    http://127.0.0.1:8000/docs")
    print("=" * 60)

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
