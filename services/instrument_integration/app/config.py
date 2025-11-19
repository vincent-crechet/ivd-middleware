"""Application configuration."""

import os
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Application settings from environment variables."""

    # Database
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./test.db"
    )
    use_real_database: bool = os.getenv("USE_REAL_DATABASE", "false").lower() == "true"

    # JWT
    jwt_secret: str = os.getenv("JWT_SECRET", "test-secret-key-change-in-production")
    jwt_algorithm: str = "HS256"

    # CORS
    cors_origins: list = ["*"]

    # API
    api_title: str = "Instrument Integration Service"
    api_version: str = "1.0.0"
    api_description: str = "Manages communication with analytical laboratory instruments"

    class Config:
        env_file = ".env"
        case_sensitive = False


# Singleton instance
settings = AppSettings()
