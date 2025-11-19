"""Pytest configuration for Verification Service tests."""

import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel

from app.models import (
    AutoVerificationSettings,
    Review,
    ResultDecision,
    VerificationRule,
    RuleType,
)
from app.adapters import (
    InMemoryAutoVerificationSettingsRepository,
    InMemoryReviewRepository,
    InMemoryResultDecisionRepository,
    InMemoryVerificationRuleRepository,
    PostgresAutoVerificationSettingsRepository,
    PostgresReviewRepository,
    PostgresResultDecisionRepository,
    PostgresVerificationRuleRepository,
)
from app.ports import (
    IAutoVerificationSettingsRepository,
    IReviewRepository,
    IResultDecisionRepository,
    IVerificationRuleRepository,
)
from app.services import (
    VerificationEngine,
    VerificationService,
    ReviewService,
    SettingsService,
)


# ============================================================================
# SQLModel Metadata Management (fixes parametrized fixture reuse)
# ============================================================================

@pytest.fixture(autouse=True)
def _refresh_sqlmodel_metadata():
    """
    Autouse fixture that clears SQLModel metadata before and after each test.

    This prevents "already exists" errors when parametrized fixtures reuse
    the same database engine across multiple test runs.
    """
    for table in list(SQLModel.metadata.tables.values()):
        table.constraints.clear()
        table.indexes.clear()

    yield

    for table in list(SQLModel.metadata.tables.values()):
        table.constraints.clear()
        table.indexes.clear()


# ============================================================================
# Database Session (PostgreSQL with SQLite in-memory for testing)
# ============================================================================

@pytest.fixture
def db_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


# ============================================================================
# Parametrized Repository Fixtures (In-Memory vs PostgreSQL)
# ============================================================================

@pytest.fixture(params=["in_memory", "postgres"], ids=["InMemory", "PostgreSQL"])
def auto_verification_settings_repository(
    request, db_session
) -> IAutoVerificationSettingsRepository:
    """Parametrized fixture providing both in-memory and PostgreSQL implementations."""
    if request.param == "in_memory":
        return InMemoryAutoVerificationSettingsRepository()
    elif request.param == "postgres":
        return PostgresAutoVerificationSettingsRepository(db_session)


@pytest.fixture(params=["in_memory", "postgres"], ids=["InMemory", "PostgreSQL"])
def review_repository(request, db_session) -> IReviewRepository:
    """Parametrized fixture providing both in-memory and PostgreSQL implementations."""
    if request.param == "in_memory":
        return InMemoryReviewRepository()
    elif request.param == "postgres":
        return PostgresReviewRepository(db_session)


@pytest.fixture(params=["in_memory", "postgres"], ids=["InMemory", "PostgreSQL"])
def result_decision_repository(
    request, db_session
) -> IResultDecisionRepository:
    """Parametrized fixture providing both in-memory and PostgreSQL implementations."""
    if request.param == "in_memory":
        return InMemoryResultDecisionRepository()
    elif request.param == "postgres":
        return PostgresResultDecisionRepository(db_session)


@pytest.fixture(params=["in_memory", "postgres"], ids=["InMemory", "PostgreSQL"])
def verification_rule_repository(
    request, db_session
) -> IVerificationRuleRepository:
    """Parametrized fixture providing both in-memory and PostgreSQL implementations."""
    if request.param == "in_memory":
        return InMemoryVerificationRuleRepository()
    elif request.param == "postgres":
        return PostgresVerificationRuleRepository(db_session)


# ============================================================================
# Service Fixtures (Using Parametrized Repositories)
# ============================================================================

@pytest.fixture
def settings_service(
    auto_verification_settings_repository, verification_rule_repository
) -> SettingsService:
    """SettingsService with parametrized repositories."""
    return SettingsService(
        settings_repo=auto_verification_settings_repository,
        rule_repo=verification_rule_repository,
    )


@pytest.fixture
def review_service(
    review_repository, result_decision_repository
) -> ReviewService:
    """ReviewService with parametrized repositories."""
    return ReviewService(
        review_repo=review_repository,
        decision_repo=result_decision_repository,
        result_repo=None,  # Mock or skip for unit tests
        sample_repo=None,  # Mock or skip for unit tests
    )


# ============================================================================
# Test Data Fixtures
# ============================================================================

TEST_TENANT_ID = "test-tenant-123"
TEST_TEST_CODE = "GLU"
TEST_TEST_NAME = "Glucose"


@pytest.fixture
def sample_settings():
    """Sample AutoVerificationSettings for testing."""
    return AutoVerificationSettings(
        id=str(uuid.uuid4()),
        tenant_id=TEST_TENANT_ID,
        test_code=TEST_TEST_CODE,
        test_name=TEST_TEST_NAME,
        reference_range_low=70.0,
        reference_range_high=100.0,
        critical_range_low=40.0,
        critical_range_high=400.0,
        instrument_flags_to_block='["C"]',
        delta_check_threshold_percent=10.0,
        delta_check_lookback_days=30,
    )


@pytest.fixture
def sample_review():
    """Sample Review for testing."""
    return Review(
        id=str(uuid.uuid4()),
        tenant_id=TEST_TENANT_ID,
        sample_id=str(uuid.uuid4()),
        reviewer_user_id=None,
        state="pending",
        decision=None,
        comments=None,
    )


@pytest.fixture
def sample_verification_rule():
    """Sample VerificationRule for testing."""
    return VerificationRule(
        id=str(uuid.uuid4()),
        tenant_id=TEST_TENANT_ID,
        rule_type=RuleType.REFERENCE_RANGE,
        enabled=True,
        priority=1,
        description="Check if value is within reference range",
    )
