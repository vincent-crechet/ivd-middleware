"""Dependency injection setup for Verification Service."""

from functools import lru_cache
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

from app.config import AppSettings
from app.ports import (
    IAutoVerificationSettingsRepository,
    IReviewRepository,
    IResultDecisionRepository,
    IVerificationRuleRepository,
)
from app.adapters import (
    PostgresAutoVerificationSettingsRepository,
    PostgresReviewRepository,
    PostgresResultDecisionRepository,
    PostgresVerificationRuleRepository,
    InMemoryAutoVerificationSettingsRepository,
    InMemoryReviewRepository,
    InMemoryResultDecisionRepository,
    InMemoryVerificationRuleRepository,
)
from app.services import (
    VerificationEngine,
    VerificationService,
    ReviewService,
    SettingsService,
)

# Import from LIS integration service for result and sample repositories
# In production, this would be done via service-to-service communication
try:
    from services.lis_integration.app.ports import (
        IResultRepository,
        ISampleRepository,
    )
    from services.lis_integration.app.adapters import (
        PostgresResultRepository,
        PostgresSampleRepository,
        InMemoryResultRepository,
        InMemorySampleRepository,
    )
    HAS_LIS_INTEGRATION = True
except ImportError:
    # Fallback for when running in isolation
    HAS_LIS_INTEGRATION = False
    from typing import Protocol

    class IResultRepository(Protocol):
        """Protocol for result repository when LIS service is not available."""
        pass

    class ISampleRepository(Protocol):
        """Protocol for sample repository when LIS service is not available."""
        pass

    class PostgresResultRepository:
        """Mock for result repository."""
        def __init__(self, session):
            self.session = session

    class PostgresSampleRepository:
        """Mock for sample repository."""
        def __init__(self, session):
            self.session = session

    class InMemoryResultRepository:
        """Mock for in-memory result repository."""
        pass

    class InMemorySampleRepository:
        """Mock for in-memory sample repository."""
        pass


logger = logging.getLogger(__name__)


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
            logger.info("Using in-memory SQLite database for local development")
        else:
            # Use configured database URL with connection pooling
            engine = create_engine(
                settings.database_url,
                pool_pre_ping=settings.db_pool_pre_ping,
                pool_size=settings.db_pool_size,
                max_overflow=settings.db_max_overflow
            )
            SQLModel.metadata.create_all(engine)
            logger.info(f"Connected to database: {settings.database_url}")

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


# Repository factories for verification service
def get_auto_verification_settings_repository(
    settings: AppSettings = Depends(get_settings),
    session: Session = Depends(get_db_session)
) -> IAutoVerificationSettingsRepository:
    """Create auto-verification settings repository based on configuration."""
    if settings.use_real_database:
        return PostgresAutoVerificationSettingsRepository(session)
    else:
        return InMemoryAutoVerificationSettingsRepository()


def get_review_repository(
    settings: AppSettings = Depends(get_settings),
    session: Session = Depends(get_db_session)
) -> IReviewRepository:
    """Create review repository based on configuration."""
    if settings.use_real_database:
        return PostgresReviewRepository(session)
    else:
        return InMemoryReviewRepository()


def get_result_decision_repository(
    settings: AppSettings = Depends(get_settings),
    session: Session = Depends(get_db_session)
) -> IResultDecisionRepository:
    """Create result decision repository based on configuration."""
    if settings.use_real_database:
        return PostgresResultDecisionRepository(session)
    else:
        return InMemoryResultDecisionRepository()


def get_verification_rule_repository(
    settings: AppSettings = Depends(get_settings),
    session: Session = Depends(get_db_session)
) -> IVerificationRuleRepository:
    """Create verification rule repository based on configuration."""
    if settings.use_real_database:
        return PostgresVerificationRuleRepository(session)
    else:
        return InMemoryVerificationRuleRepository()


# Repository factories for LIS integration
def get_result_repository(
    settings: AppSettings = Depends(get_settings),
    session: Session = Depends(get_db_session)
) -> Optional[IResultRepository]:
    """
    Create result repository for accessing test results.

    This repository is from the LIS integration service.
    In a microservices architecture, this would be replaced with
    service-to-service communication.
    """
    if not HAS_LIS_INTEGRATION:
        logger.warning("LIS integration not available - result repository unavailable")
        return None

    if settings.use_real_database:
        return PostgresResultRepository(session)
    else:
        return InMemoryResultRepository()


def get_sample_repository(
    settings: AppSettings = Depends(get_settings),
    session: Session = Depends(get_db_session)
) -> Optional[ISampleRepository]:
    """
    Create sample repository for accessing samples.

    This repository is from the LIS integration service.
    In a microservices architecture, this would be replaced with
    service-to-service communication.
    """
    if not HAS_LIS_INTEGRATION:
        logger.warning("LIS integration not available - sample repository unavailable")
        return None

    if settings.use_real_database:
        return PostgresSampleRepository(session)
    else:
        return InMemorySampleRepository()


# Verification engine factory
def get_verification_engine(
    settings_repo: IAutoVerificationSettingsRepository = Depends(get_auto_verification_settings_repository),
    rules_repo: IVerificationRuleRepository = Depends(get_verification_rule_repository),
    result_repo: Optional[IResultRepository] = Depends(get_result_repository)
) -> VerificationEngine:
    """
    Create verification engine with injected dependencies.

    The engine applies verification rules to test results to determine
    if they can be auto-verified or need manual review.
    """
    return VerificationEngine(
        settings_repository=settings_repo,
        rules_repository=rules_repo,
        result_repository=result_repo
    )


# Business service factories
def get_verification_service(
    settings_repo: IAutoVerificationSettingsRepository = Depends(get_auto_verification_settings_repository),
    result_repo: Optional[IResultRepository] = Depends(get_result_repository),
    engine: VerificationEngine = Depends(get_verification_engine)
) -> VerificationService:
    """
    Create verification service with injected dependencies.

    The service orchestrates verification of test results including
    applying rules, updating statuses, and managing verification workflow.
    """
    if result_repo is None:
        logger.warning("Creating VerificationService without result repository")

    return VerificationService(
        settings_repository=settings_repo,
        result_repository=result_repo,
        verification_engine=engine
    )


def get_review_service(
    review_repo: IReviewRepository = Depends(get_review_repository),
    decision_repo: IResultDecisionRepository = Depends(get_result_decision_repository),
    result_repo: Optional[IResultRepository] = Depends(get_result_repository),
    sample_repo: Optional[ISampleRepository] = Depends(get_sample_repository)
) -> ReviewService:
    """
    Create review service with injected dependencies.

    The service manages manual review workflow for test results that
    failed auto-verification, including approval, rejection, and escalation.
    """
    if result_repo is None or sample_repo is None:
        logger.warning("Creating ReviewService with missing repositories")

    return ReviewService(
        review_repository=review_repo,
        result_decision_repository=decision_repo,
        result_repository=result_repo,
        sample_repository=sample_repo
    )


def get_settings_service(
    settings_repo: IAutoVerificationSettingsRepository = Depends(get_auto_verification_settings_repository),
    rules_repo: IVerificationRuleRepository = Depends(get_verification_rule_repository)
) -> SettingsService:
    """
    Create settings service with injected dependencies.

    The service manages configuration of verification rules and settings
    including reference ranges, critical ranges, and delta check parameters.
    """
    return SettingsService(
        settings_repository=settings_repo,
        rules_repository=rules_repo
    )


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

    Returns user information including tenant_id, user_id, and role.
    Used for authorization and audit trail.
    """
    token = credentials.credentials

    # TODO: In production, validate JWT token with Platform Service
    # Extract user information from token including role-based permissions

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing token"
        )

    # Placeholder user info
    return {
        "tenant_id": "default-tenant",
        "user_id": "default-user",
        "role": "admin"  # Possible roles: admin, reviewer, pathologist
    }


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """
    Get current user from JWT token if available, otherwise return None.

    Used for endpoints that support both authenticated and unauthenticated access.
    """
    if not credentials:
        return None

    try:
        return get_current_user(credentials)
    except HTTPException:
        return None
