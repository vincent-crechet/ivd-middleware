"""Pytest configuration and fixtures for Platform Service tests."""

import pytest
from app.adapters import (
    InMemoryTenantRepository,
    InMemoryUserRepository,
    BcryptPasswordHasher
)


# In-memory fixtures
@pytest.fixture
def in_memory_tenant_repo():
    """Fresh in-memory tenant repository for each test."""
    return InMemoryTenantRepository()


@pytest.fixture
def in_memory_user_repo():
    """Fresh in-memory user repository for each test."""
    return InMemoryUserRepository()


@pytest.fixture
def password_hasher():
    """Password hasher for tests."""
    return BcryptPasswordHasher()


# TODO: Add PostgreSQL fixtures when needed for integration tests
