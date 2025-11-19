"""Application configuration for Verification Service."""

from pydantic_settings import BaseSettings
from typing import List


class AppSettings(BaseSettings):
    """Application settings with environment variable support."""

    # Service settings
    service_name: str = "Verification Service"
    environment: str = "local"  # local, development, production

    # Database settings
    database_url: str = "postgresql://localhost/ivd_middleware"
    use_real_database: bool = True

    # JWT settings for token validation
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_audience: str = "ivd-middleware"
    jwt_issuer: str = "platform-service"

    # API settings
    api_v1_prefix: str = "/api/v1"
    api_title: str = "Verification Service"
    api_description: str = "Service for automated verification and manual review of test results"
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
    server_port: int = 8002

    # Logging settings
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Verification engine settings
    verification_batch_size: int = 100
    enable_auto_verification: bool = True
    enable_delta_check: bool = False  # Requires result repository integration

    # Review queue settings
    review_queue_default_limit: int = 50
    review_queue_max_limit: int = 500

    # Feature flags
    enable_review_escalation: bool = True
    enable_audit_trail: bool = True
    enable_notification_service: bool = False  # Future: notify reviewers

    # Integration settings
    lis_service_url: str = "http://localhost:8001"
    platform_service_url: str = "http://localhost:8000"

    # Performance settings
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_pre_ping: bool = True

    # Default verification rule settings
    initialize_default_rules_on_startup: bool = True

    class Config:
        """Pydantic config."""
        env_file = ".env"
        case_sensitive = False
        env_prefix = "VERIFICATION_"
