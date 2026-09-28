"""
Application Configuration
Loads settings and environment variables securely using python-dotenv.
Never logs or exposes sensitive API keys.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file if present
load_dotenv(dotenv_path=BASE_DIR / ".env")


class Settings:
    """Application settings class with safe defaults."""

    # Gemini AI Configuration
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_WORKOUT_MODEL: str = os.getenv("GEMINI_WORKOUT_MODEL", "gemini-2.5-flash").strip()
    GEMINI_TIP_MODEL: str = os.getenv("GEMINI_TIP_MODEL", "gemini-2.5-flash").strip()

    # Database Configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./fitbuddy.db").strip()

    # Admin Dashboard Authentication
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin").strip()
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123").strip()

    # Session Management
    SECRET_KEY: str = os.getenv("SECRET_KEY", "fitbuddy-secure-session-key-dev-32chars").strip()
    APP_ENV: str = os.getenv("APP_ENV", "development").strip().lower()

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def has_gemini_api_key(self) -> bool:
        return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY != "your_api_key_here")


settings = Settings()
