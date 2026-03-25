"""
Application configuration loaded from environment variables / .env file.

Settings are validated by Pydantic at startup.  The ``get_settings``
function is cached with ``lru_cache`` so the heavy Pydantic parsing only
runs once per process.
"""
from functools import lru_cache
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    All runtime configuration values for the LACE backend.

    Values are read from environment variables (case-sensitive) or from a
    ``.env`` file in the working directory.  Fields without a ``default``
    are required and will raise a validation error if missing.
    """

    # Database
    DATABASE_URL: str
    """SQLAlchemy connection string, e.g. ``sqlite:///./lace.db`` or a PostgreSQL URL."""

    # Security
    SECRET_KEY: str = Field(..., min_length=32)
    """Secret key used to sign JWT tokens.  Must be at least 32 characters."""
    ALGORITHM: str = "HS256"
    """JWT signing algorithm."""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    """Lifetime of an access token in minutes."""
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    """Lifetime of a refresh token in days."""

    # Password policy
    PASSWORD_MIN_LENGTH: int = 8
    """Minimum accepted password length."""
    PASSWORD_REQUIRE_DIGIT: bool = False
    """Whether passwords must contain at least one digit."""
    PASSWORD_REQUIRE_LETTER: bool = True
    """Whether passwords must contain at least one letter."""

    # Auth rate limiting
    AUTH_RATE_LIMIT_REQUESTS: int = 10
    """Maximum number of auth attempts allowed within the rate-limit window."""
    AUTH_RATE_LIMIT_WINDOW_SECONDS: int = 60
    """Duration of the rate-limit window in seconds."""

    # CORS - explicit per environment
    CORS_ORIGINS: List[str]
    """Allowed CORS origins.  Must be set explicitly to avoid open CORS."""

    # Upload/import limits
    MAX_UPLOAD_MB: int = 10
    """Maximum size in megabytes for uploaded files."""
    MAX_IMPORT_ROWS: int = 50000
    """Maximum number of data rows accepted in a single CSV/JSON import."""

    # Admin user (created on first run)
    FIRST_ADMIN_USERNAME: Optional[str] = None
    """Username for the bootstrap admin account created at startup (optional)."""
    FIRST_ADMIN_PASSWORD: Optional[str] = None
    """Password for the bootstrap admin account created at startup (optional)."""

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        """Alias for ``DATABASE_URL``, used by SQLAlchemy engine creation helpers."""
        return self.DATABASE_URL



@lru_cache()
def get_settings() -> Settings:
    """
    Return the cached application settings singleton.

    The first call reads and validates the environment; subsequent calls
    return the already-parsed ``Settings`` object without re-reading.

    Returns:
        Settings: The validated application configuration.
    """
    return Settings()
