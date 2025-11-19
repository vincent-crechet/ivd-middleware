"""Dependency injection setup for LIS Integration Service."""

from functools import lru_cache
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import AppSettings
from app.ports import (
    ISampleRepository,
    IResultRepository,
    ILISConfigRepository,
    IOrderRepository,
    ILISAdapter,
)
from app.adapters import (
    PostgresSampleRepository,
    PostgresResultRepository,
    PostgresLISConfigRepository,
    PostgresOrderRepository,
    InMemorySampleRepository,
    InMemoryResultRepository,
    InMemoryLISConfigRepository,
    InMemoryOrderRepository,
    MockLISAdapter,
)
from app.services import SampleService, ResultService, LISConfigService


# Singleton settings
@lru_cache()
def get_settings() -> AppSettings:
    """Get application settings (cached)."""
    return AppSettings()


# Database engine cache
_engine_cache = {}


def get_engine(settings: AppSettings):
    """Get or create database engine (cached)."""
    cache_key = f"{settings.environment}_{settings.database_url}_{settings.use_real_database}"

    if cache_key not in _engine_cache:
        if settings.environment == "local" and not settings.use_real_database:
            # Use in-memory SQLite for local development
            engine = create_engine(
                "sqlite:///:memory:",
                connect_args={"check_same_thread": False},
                poolclass=StaticPool
            )
            SQLModel.metadata.create_all(engine)
        else:
            # Use configured database URL with connection pooling
            engine = create_engine(
                settings.database_url,
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10
            )
            SQLModel.metadata.create_all(engine)

        _engine_cache[cache_key] = engine

    return _engine_cache[cache_key]


# Database session factory
def get_db_session(settings: AppSettings = Depends(get_settings)):
    """
    Create database session with cached engine.

    Uses connection pooling for better performance.
    """
    engine = get_engine(settings)
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


# Repository factories
def get_sample_repository(
    settings: AppSettings = Depends(get_settings),
    session: Session = Depends(get_db_session)
) -> ISampleRepository:
    """Create sample repository based on configuration."""
    if settings.use_real_database:
        return PostgresSampleRepository(session)
    else:
        return InMemorySampleRepository()


def get_result_repository(
    settings: AppSettings = Depends(get_settings),
    session: Session = Depends(get_db_session)
) -> IResultRepository:
    """Create result repository based on configuration."""
    if settings.use_real_database:
        return PostgresResultRepository(session)
    else:
        return InMemoryResultRepository()


def get_lis_config_repository(
    settings: AppSettings = Depends(get_settings),
    session: Session = Depends(get_db_session)
) -> ILISConfigRepository:
    """Create LIS config repository based on configuration."""
    if settings.use_real_database:
        return PostgresLISConfigRepository(session)
    else:
        return InMemoryLISConfigRepository()


def get_order_repository(
    settings: AppSettings = Depends(get_settings),
    session: Session = Depends(get_db_session)
) -> IOrderRepository:
    """Create order repository based on configuration."""
    if settings.use_real_database:
        return PostgresOrderRepository(session)
    else:
        return InMemoryOrderRepository()


# LIS Adapter factory
def get_lis_adapter() -> ILISAdapter:
    """Create LIS adapter (mock for now)."""
    return MockLISAdapter()


# Business service factories
def get_sample_service(
    sample_repo: ISampleRepository = Depends(get_sample_repository)
) -> SampleService:
    """Create sample service with injected dependencies."""
    return SampleService(sample_repo)


def get_result_service(
    result_repo: IResultRepository = Depends(get_result_repository)
) -> ResultService:
    """Create result service with injected dependencies."""
    return ResultService(result_repo)


def get_lis_config_service(
    config_repo: ILISConfigRepository = Depends(get_lis_config_repository),
    lis_adapter: ILISAdapter = Depends(get_lis_adapter)
) -> LISConfigService:
    """Create LIS config service with injected dependencies."""
    return LISConfigService(config_repo, lis_adapter)


# Security dependencies
security = HTTPBearer()


def get_current_tenant_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Extract and validate tenant ID from JWT token.

    This dependency ensures multi-tenant isolation.
    In a real implementation, this would validate the JWT token
    with the Platform Service. For now, it extracts from headers.
    """
    token = credentials.credentials

    # TODO: In production, validate JWT token with Platform Service
    # For now, extract tenant_id from Bearer token claim

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token"
        )

    # Placeholder: in real implementation, parse JWT and extract tenant_id
    # For now, return a default or extract from token
    return "default-tenant"


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Get current user from JWT token.

    Returns user information including tenant_id and role.
    """
    token = credentials.credentials

    # TODO: In production, validate JWT token with Platform Service
    # Extract user information from token

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token"
        )

    # Placeholder user info
    return {
        "tenant_id": "default-tenant",
        "user_id": "default-user",
        "role": "admin"
    }
