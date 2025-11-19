"""Application configuration for LIS Integration Service."""

from pydantic_settings import BaseSettings
from typing import List


class AppSettings(BaseSettings):
    """Application settings with environment variable support."""

    # Service settings
    service_name: str = "LIS Integration Service"
    environment: str = "local"  # local, development, production

    # Database settings
    database_url: str = "postgresql://localhost/ivd_middleware"
    use_real_database: bool = True

    # JWT settings
    secret_key: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"

    # API settings
    api_v1_prefix: str = "/api/v1"
    api_title: str = "LIS Integration Service"
    api_description: str = "Service for Lab Information System integration"
    api_version: str = "1.0.0"

    # CORS settings
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://0.0.0.0:3000",
        "http://0.0.0.0:5173",
    ]

    # Server settings
    server_host: str = "0.0.0.0"
    server_port: int = 8001

    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = False
