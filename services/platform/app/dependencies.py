"""Dependency injection setup for Platform Service."""

from functools import lru_cache
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import AppSettings
from app.ports import (
    ITenantRepository,
    IUserRepository,
    IPasswordHasher,
    IAuthenticationService
)
from app.adapters import (
    PostgresTenantRepository,
    PostgresUserRepository,
    InMemoryTenantRepository,
    InMemoryUserRepository,
    BcryptPasswordHasher,
    JWTAuthenticationService
)
from app.services import TenantService, UserService, AuthService, TenantAdminService


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
def get_tenant_repository(
    settings: AppSettings = Depends(get_settings),
    session: Session = Depends(get_db_session)
) -> ITenantRepository:
    """Create tenant repository based on configuration."""
    if settings.use_real_database:
        return PostgresTenantRepository(session)
    else:
        return InMemoryTenantRepository()


def get_user_repository(
    settings: AppSettings = Depends(get_settings),
    session: Session = Depends(get_db_session)
) -> IUserRepository:
    """Create user repository based on configuration."""
    if settings.use_real_database:
        return PostgresUserRepository(session)
    else:
        return InMemoryUserRepository()


# Infrastructure service factories
def get_password_hasher() -> IPasswordHasher:
    """Create password hasher."""
    return BcryptPasswordHasher()


def get_authentication_service(
    settings: AppSettings = Depends(get_settings)
) -> IAuthenticationService:
    """Create authentication service."""
    return JWTAuthenticationService(
        secret_key=settings.secret_key,
        algorithm=settings.jwt_algorithm
    )


# Business service factories
def get_tenant_service(
    tenant_repo: ITenantRepository = Depends(get_tenant_repository)
) -> TenantService:
    """Create tenant service with injected dependencies."""
    return TenantService(tenant_repo)


def get_user_service(
    user_repo: IUserRepository = Depends(get_user_repository),
    password_hasher: IPasswordHasher = Depends(get_password_hasher)
) -> UserService:
    """Create user service with injected dependencies."""
    return UserService(user_repo, password_hasher)


def get_auth_service(
    user_repo: IUserRepository = Depends(get_user_repository),
    password_hasher: IPasswordHasher = Depends(get_password_hasher),
    auth_service: IAuthenticationService = Depends(get_authentication_service)
) -> AuthService:
    """Create auth service with injected dependencies."""
    return AuthService(user_repo, password_hasher, auth_service)


def get_tenant_admin_service(
    tenant_repo: ITenantRepository = Depends(get_tenant_repository),
    user_repo: IUserRepository = Depends(get_user_repository),
    password_hasher: IPasswordHasher = Depends(get_password_hasher)
) -> TenantAdminService:
    """Create tenant admin service with injected dependencies."""
    return TenantAdminService(tenant_repo, user_repo, password_hasher)


# Security dependencies
security = HTTPBearer()


def get_current_tenant_id(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> str:
    """
    Extract and validate tenant ID from JWT token.

    This dependency ensures multi-tenant isolation.
    """
    token = credentials.credentials
    payload = auth_service.verify_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    tenant_id = payload.get("tenant_id")
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing tenant context"
        )

    return tenant_id


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> dict:
    """
    Get current user from JWT token.

    Returns user information including tenant_id and role.
    """
    token = credentials.credentials
    user = auth_service.get_current_user(token)
    return user
