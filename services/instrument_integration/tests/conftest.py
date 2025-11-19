"""Pytest configuration and fixtures for Instrument Integration Service tests."""

import pytest
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from app.adapters import (
    InMemoryInstrumentRepository,
    InMemoryOrderRepository,
    InMemoryInstrumentQueryRepository,
    InMemoryInstrumentResultRepository,
    PostgresInstrumentRepository,
    PostgresOrderRepository,
    PostgresInstrumentQueryRepository,
    PostgresInstrumentResultRepository,
)
from app.services import (
    InstrumentService,
    OrderService,
    InstrumentQueryService,
    InstrumentResultService,
)

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
    """Refresh SQLModel metadata before and after each test."""
    for table in list(SQLModel.metadata.tables.values()):
        table.constraints.clear()
        table.indexes.clear()

    yield

    for table in list(SQLModel.metadata.tables.values()):
        table.constraints.clear()
        table.indexes.clear()


# ===== In-Memory Fixtures =====
@pytest.fixture
def in_memory_instrument_repo():
    """Fresh in-memory instrument repository for each test."""
    return InMemoryInstrumentRepository()


@pytest.fixture
def in_memory_order_repo():
    """Fresh in-memory order repository for each test."""
    return InMemoryOrderRepository()


@pytest.fixture
def in_memory_instrument_query_repo():
    """Fresh in-memory instrument query repository for each test."""
    return InMemoryInstrumentQueryRepository()


@pytest.fixture
def in_memory_instrument_result_repo():
    """Fresh in-memory instrument result repository for each test."""
    return InMemoryInstrumentResultRepository()


# ===== PostgreSQL Fixtures =====
@pytest.fixture(scope="function")
def db_session():
    """Provide a clean database session for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    try:
        SQLModel.metadata.create_all(engine)
    except Exception as e:
        if "already exists" not in str(e).lower():
            raise

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
def postgres_instrument_repo(db_session):
    """Fresh PostgreSQL instrument repository for each test."""
    return PostgresInstrumentRepository(db_session)


@pytest.fixture
def postgres_order_repo(db_session):
    """Fresh PostgreSQL order repository for each test."""
    return PostgresOrderRepository(db_session)


@pytest.fixture
def postgres_instrument_query_repo(db_session):
    """Fresh PostgreSQL instrument query repository for each test."""
    return PostgresInstrumentQueryRepository(db_session)


@pytest.fixture
def postgres_instrument_result_repo(db_session):
    """Fresh PostgreSQL instrument result repository for each test."""
    return PostgresInstrumentResultRepository(db_session)


# ===== Parametrized Fixtures for Shared Tests =====
@pytest.fixture(params=["in_memory", "postgres"], ids=["InMemory", "PostgreSQL"])
def instrument_repository(request, in_memory_instrument_repo, postgres_instrument_repo):
    """Parametrized fixture that provides instrument repository for both adapters."""
    if request.param == "in_memory":
        return in_memory_instrument_repo
    elif request.param == "postgres":
        return postgres_instrument_repo


@pytest.fixture(params=["in_memory", "postgres"], ids=["InMemory", "PostgreSQL"])
def order_repository(request, in_memory_order_repo, postgres_order_repo):
    """Parametrized fixture that provides order repository for both adapters."""
    if request.param == "in_memory":
        return in_memory_order_repo
    elif request.param == "postgres":
        return postgres_order_repo


@pytest.fixture(params=["in_memory", "postgres"], ids=["InMemory", "PostgreSQL"])
def instrument_query_repository(request, in_memory_instrument_query_repo, postgres_instrument_query_repo):
    """Parametrized fixture that provides instrument query repository for both adapters."""
    if request.param == "in_memory":
        return in_memory_instrument_query_repo
    elif request.param == "postgres":
        return postgres_instrument_query_repo


@pytest.fixture(params=["in_memory", "postgres"], ids=["InMemory", "PostgreSQL"])
def instrument_result_repository(request, in_memory_instrument_result_repo, postgres_instrument_result_repo):
    """Parametrized fixture that provides instrument result repository for both adapters."""
    if request.param == "in_memory":
        return in_memory_instrument_result_repo
    elif request.param == "postgres":
        return postgres_instrument_result_repo


# ===== Service Fixtures =====
@pytest.fixture
def instrument_service(instrument_repository):
    """Create instrument service with injected repository."""
    return InstrumentService(instrument_repository)


@pytest.fixture
def order_service(order_repository):
    """Create order service with injected repository."""
    return OrderService(order_repository)


@pytest.fixture
def instrument_query_service(instrument_query_repository):
    """Create instrument query service with injected repository."""
    return InstrumentQueryService(instrument_query_repository)


@pytest.fixture
def instrument_result_service(instrument_result_repository):
    """Create instrument result service with injected repository."""
    return InstrumentResultService(instrument_result_repository)
