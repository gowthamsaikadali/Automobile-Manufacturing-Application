import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _get_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    return database_url


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(
        os.getenv("DATABASE_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
        or f"sqlite:///{BASE_DIR / 'app.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    _DEFAULT_ENGINE_OPTIONS = {"pool_pre_ping": True}
    if not SQLALCHEMY_DATABASE_URI.startswith("sqlite"):
        _DEFAULT_ENGINE_OPTIONS.update(
            {
                "pool_recycle": _get_int("DB_POOL_RECYCLE", 280),
                "pool_size": _get_int("DB_POOL_SIZE", 5),
                "max_overflow": _get_int("DB_MAX_OVERFLOW", 10),
                "pool_timeout": _get_int("DB_POOL_TIMEOUT", 30),
            }
        )
    SQLALCHEMY_ENGINE_OPTIONS = _DEFAULT_ENGINE_OPTIONS

    APP_NAME = os.getenv("APP_NAME", "Automobile Manufacturing Dashboard")
    DEBUG = _get_bool("FLASK_DEBUG", "false")
    ENV = os.getenv("FLASK_ENV", "production")
    PER_PAGE = _get_int("PER_PAGE", 25)
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    PREFERRED_URL_SCHEME = os.getenv(
        "PREFERRED_URL_SCHEME", "http" if DEBUG else "https"
    )

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")
    SESSION_COOKIE_SECURE = _get_bool(
        "SESSION_COOKIE_SECURE", "false" if DEBUG else "true"
    )
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = SESSION_COOKIE_SECURE
    REMEMBER_COOKIE_SAMESITE = SESSION_COOKIE_SAMESITE
    PERMANENT_SESSION_LIFETIME = timedelta(
        minutes=_get_int("SESSION_LIFETIME_MINUTES", 60)
    )
    WTF_CSRF_TIME_LIMIT = None

    DEFAULT_ADMIN_USERNAME = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    DEFAULT_ADMIN_PASSWORD = os.getenv("DEFAULT_ADMIN_PASSWORD", "Admin@123")
    HEALTHCHECK_TOKEN = os.getenv("HEALTHCHECK_TOKEN")
