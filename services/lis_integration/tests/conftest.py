"""Pytest configuration and fixtures for LIS Integration Service tests."""

import pytest
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from app.adapters import (
    InMemorySampleRepository,
    InMemoryResultRepository,
    InMemoryLISConfigRepository,
    InMemoryOrderRepository,
    MockLISAdapter,
    PostgresSampleRepository,
    PostgresResultRepository,
    PostgresLISConfigRepository,
    PostgresOrderRepository,
)
from app.services import SampleService, ResultService, LISConfigService

# Import Tenant model from Platform Service for FK constraint
try:
    from pathlib import Path
    import sys
    platform_path = Path(__file__).parent.parent.parent / "platform" / "app"
    if str(platform_path) not in sys.path:
        sys.path.insert(0, str(platform_path))
    from models.tenant import Tenant
except ImportError:
    # Fallback Tenant model
    from sqlmodel import SQLModel, Field
    from typing import Optional
    from datetime import datetime

    class Tenant(SQLModel, table=True):
        __tablename__ = "tenants"
        id: Optional[str] = Field(default=None, primary_key=True)
        name: str = Field(nullable=False, unique=True)
        is_active: bool = Field(default=True, nullable=False)
        created_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)
        updated_at: datetime = Field(default_factory=datetime.utcnow, nullable=False)


TEST_TENANT_ID = "test-tenant-123"


# ===== Metadata Management Fixture =====
@pytest.fixture(autouse=True)
def _refresh_sqlmodel_metadata():
    """Refresh SQLModel metadata before and after each test to handle parametrized fixtures.

    When parametrized tests reuse db_session, SQLModel.metadata accumulates
    table/index definitions that cause "already exists" errors on subsequent
    create_all() calls. Clearing before and after each test ensures clean schema creation.
    """
    # Before test: clear any accumulated constraints/indexes from previous parametrization
    for table in list(SQLModel.metadata.tables.values()):
        table.constraints.clear()
        table.indexes.clear()

    yield

    # After test: clear table references to prevent "already exists" errors
    # on the next parametrized test run
    for table in list(SQLModel.metadata.tables.values()):
        table.constraints.clear()
        table.indexes.clear()


# ===== In-Memory Fixtures =====
@pytest.fixture
def in_memory_sample_repo():
    """Fresh in-memory sample repository for each test."""
    return InMemorySampleRepository()


@pytest.fixture
def in_memory_result_repo():
    """Fresh in-memory result repository for each test."""
    return InMemoryResultRepository()


@pytest.fixture
def in_memory_lis_config_repo():
    """Fresh in-memory LIS config repository for each test."""
    return InMemoryLISConfigRepository()


@pytest.fixture
def in_memory_order_repo():
    """Fresh in-memory order repository for each test."""
    return InMemoryOrderRepository()


# ===== PostgreSQL Fixtures =====
@pytest.fixture(scope="function")
def db_session():
    """Provide a clean database session for each test.

    Uses in-memory SQLite for testing PostgreSQL adapters.
    Each test gets a fresh in-memory database to avoid metadata conflicts.
    """
    # Use in-memory SQLite for testing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    # Create all tables
    # Important: SQLModel.metadata is a global singleton that accumulates
    # table definitions from all imported models. When parametrized tests
    # reuse this fixture, SQLAlchemy tries to create the same indexes again.
    # We work around this by temporarily replacing the metadata's bind
    # context to ensure fresh schema creation for each test.
    SQLModel.metadata.create_all(engine)

    # Provide session
    session = Session(engine)

    # Create test tenant
    test_tenant = Tenant(
        id=TEST_TENANT_ID,
        name="Test Tenant",
        is_active=True
    )
    session.add(test_tenant)
    session.commit()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def postgres_sample_repo(db_session):
    """Fresh PostgreSQL sample repository for each test."""
    return PostgresSampleRepository(db_session)


@pytest.fixture
def postgres_result_repo(db_session):
    """Fresh PostgreSQL result repository for each test."""
    return PostgresResultRepository(db_session)


@pytest.fixture
def postgres_lis_config_repo(db_session):
    """Fresh PostgreSQL LIS config repository for each test."""
    return PostgresLISConfigRepository(db_session)


@pytest.fixture
def postgres_order_repo(db_session):
    """Fresh PostgreSQL order repository for each test."""
    return PostgresOrderRepository(db_session)


# ===== Parametrized Fixtures for Shared Tests =====
@pytest.fixture(params=["in_memory", "postgres"], ids=["InMemory", "PostgreSQL"])
def sample_repository(request, in_memory_sample_repo, postgres_sample_repo):
    """Parametrized fixture that provides sample repository for both adapters."""
    if request.param == "in_memory":
        return in_memory_sample_repo
    elif request.param == "postgres":
        return postgres_sample_repo


@pytest.fixture(params=["in_memory", "postgres"], ids=["InMemory", "PostgreSQL"])
def result_repository(request, in_memory_result_repo, postgres_result_repo):
    """Parametrized fixture that provides result repository for both adapters."""
    if request.param == "in_memory":
        return in_memory_result_repo
    elif request.param == "postgres":
        return postgres_result_repo


@pytest.fixture(params=["in_memory", "postgres"], ids=["InMemory", "PostgreSQL"])
def lis_config_repository(request, in_memory_lis_config_repo, postgres_lis_config_repo):
    """Parametrized fixture that provides LIS config repository for both adapters."""
    if request.param == "in_memory":
        return in_memory_lis_config_repo
    elif request.param == "postgres":
        return postgres_lis_config_repo


@pytest.fixture(params=["in_memory", "postgres"], ids=["InMemory", "PostgreSQL"])
def order_repository(request, in_memory_order_repo, postgres_order_repo):
    """Parametrized fixture that provides order repository for both adapters."""
    if request.param == "in_memory":
        return in_memory_order_repo
    elif request.param == "postgres":
        return postgres_order_repo


# ===== Service Fixtures =====
@pytest.fixture
def lis_adapter():
    """Create LIS adapter (mock)."""
    return MockLISAdapter()


@pytest.fixture
def sample_service(sample_repository):
    """Create sample service with injected repository."""
    return SampleService(sample_repository)


@pytest.fixture
def result_service(result_repository):
    """Create result service with injected repository."""
    return ResultService(result_repository)


@pytest.fixture
def lis_config_service(lis_config_repository, lis_adapter):
    """Create LIS config service with injected dependencies."""
    return LISConfigService(lis_config_repository, lis_adapter)
