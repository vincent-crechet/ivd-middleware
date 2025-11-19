"""Pytest configuration and fixtures for Platform Service tests."""

import pytest
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from app.adapters import (
    InMemoryTenantRepository,
    InMemoryUserRepository,
    PostgresTenantRepository,
    PostgresUserRepository,
    BcryptPasswordHasher
)
from app.models import Tenant, User


# ===== In-Memory Fixtures =====
@pytest.fixture
def in_memory_tenant_repo():
    """Fresh in-memory tenant repository for each test."""
    return InMemoryTenantRepository()


@pytest.fixture
def in_memory_user_repo():
    """Fresh in-memory user repository for each test."""
    return InMemoryUserRepository()


# ===== PostgreSQL Fixtures =====
@pytest.fixture(scope="function")
def db_session():
    """Provide a clean database session for each test.

    Uses in-memory SQLite for testing PostgreSQL adapters.
    For real PostgreSQL testing, use docker-compose.test.yml
    """
    # Use in-memory SQLite for testing
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )

    # Create all tables
    SQLModel.metadata.create_all(engine)

    # Provide session
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def postgres_tenant_repo(db_session):
    """Fresh PostgreSQL tenant repository for each test."""
    return PostgresTenantRepository(db_session)


@pytest.fixture
def postgres_user_repo(db_session):
    """Fresh PostgreSQL user repository for each test."""
    return PostgresUserRepository(db_session)


# ===== Parametrized Fixtures for Shared Tests =====
@pytest.fixture(params=["in_memory", "postgres"], ids=["InMemory", "PostgreSQL"])
def tenant_repo(request, in_memory_tenant_repo, postgres_tenant_repo):
    """Parametrized fixture that provides tenant repository for both adapters.

    This fixture automatically runs tests twice:
    1. With in-memory adapter (fast)
    2. With PostgreSQL adapter (via SQLite in-memory)

    Tests using this fixture run against both implementations without duplication.
    """
    if request.param == "in_memory":
        return in_memory_tenant_repo
    elif request.param == "postgres":
        return postgres_tenant_repo


@pytest.fixture(params=["in_memory", "postgres"], ids=["InMemory", "PostgreSQL"])
def user_repo(request, in_memory_user_repo, postgres_user_repo):
    """Parametrized fixture that provides user repository for both adapters.

    This fixture automatically runs tests twice:
    1. With in-memory adapter (fast)
    2. With PostgreSQL adapter (via SQLite in-memory)

    Tests using this fixture run against both implementations without duplication.
    """
    if request.param == "in_memory":
        return in_memory_user_repo
    elif request.param == "postgres":
        return postgres_user_repo


# ===== Utility Fixtures =====
@pytest.fixture
def password_hasher():
    """Password hasher for tests."""
    return BcryptPasswordHasher()


@pytest.fixture
def test_tenant(tenant_repo):
    """Create a test tenant for user tests.

    Works with both in-memory and PostgreSQL adapters.
    """
    tenant = Tenant(name="Test Lab", is_active=True)
    return tenant_repo.create(tenant)
