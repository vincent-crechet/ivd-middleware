"""Configuration for Platform Service."""

from pydantic_settings import BaseSettings
from typing import Optional


class AppSettings(BaseSettings):
    """Application settings with environment-specific configuration."""

    # Deployment
    environment: str = "local"  # local, docker, production
    service_name: str = "platform-service"

    # Database
    database_url: str = "sqlite:///./platform.db"

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_seconds: int = 28800  # 8 hours

    # Feature flags
    use_real_database: bool = False

    # API
    api_v1_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8080"]

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
