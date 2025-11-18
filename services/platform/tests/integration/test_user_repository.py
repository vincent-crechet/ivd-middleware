"""Integration tests for UserRepository with real database."""

import pytest
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from app.adapters import PostgresUserRepository, PostgresTenantRepository
from app.models import User, Tenant, UserRole
from app.exceptions import DuplicateUserError, UserNotFoundError


@pytest.fixture(scope="function")
def db_session():
    """Provide a clean database session for each test."""
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
def user_repo(db_session):
    """Provide PostgreSQL user repository with test database."""
    return PostgresUserRepository(db_session)


@pytest.fixture
def tenant_repo(db_session):
    """Provide PostgreSQL tenant repository with test database."""
    return PostgresTenantRepository(db_session)


@pytest.fixture
def test_tenant(tenant_repo):
    """Create a test tenant."""
    tenant = Tenant(name="Test Lab", is_active=True)
    return tenant_repo.create(tenant)


class TestPostgresUserRepository:
    """Integration tests for PostgreSQL User Repository."""

    def test_create_user(self, user_repo, test_tenant):
        """Test creating a user in database."""
        # Arrange
        user = User(
            tenant_id=test_tenant.id,
            email="john@example.com",
            password_hash="hashed_password",
            name="John Doe",
            role=UserRole.TECHNICIAN,
            is_active=True
        )

        # Act
        created = user_repo.create(user)

        # Assert
        assert created.id is not None
        assert created.email == "john@example.com"
        assert created.tenant_id == test_tenant.id
        assert created.role == UserRole.TECHNICIAN
        assert created.created_at is not None

    def test_create_user_without_tenant_id(self, user_repo):
        """Test that creating user without tenant_id raises error."""
        # Arrange
        user = User(
            email="john@example.com",
            password_hash="hashed_password",
            name="John Doe",
            role=UserRole.TECHNICIAN,
            is_active=True
        )

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            user_repo.create(user)

        assert "tenant_id" in str(exc_info.value)

    def test_create_user_duplicate_email_same_tenant(self, user_repo, test_tenant):
        """Test that duplicate email in same tenant is rejected by composite unique constraint."""
        # Arrange
        user1 = User(
            tenant_id=test_tenant.id,
            email="john@example.com",
            password_hash="hashed",
            name="John Doe",
            role=UserRole.TECHNICIAN,
            is_active=True
        )
        user_repo.create(user1)

        # Act & Assert
        user2 = User(
            tenant_id=test_tenant.id,
            email="john@example.com",
            password_hash="hashed",
            name="John Smith",
            role=UserRole.TECHNICIAN,
            is_active=True
        )
        with pytest.raises(DuplicateUserError):
            user_repo.create(user2)

    def test_create_user_same_email_different_tenant(self, user_repo, tenant_repo):
        """Test that same email in different tenant is allowed."""
        # Arrange
        tenant1 = tenant_repo.create(Tenant(name="Lab 1", is_active=True))
        tenant2 = tenant_repo.create(Tenant(name="Lab 2", is_active=True))

        user1 = User(
            tenant_id=tenant1.id,
            email="john@example.com",
            password_hash="hashed",
            name="John Doe",
            role=UserRole.TECHNICIAN,
            is_active=True
        )

        # Act
        created1 = user_repo.create(user1)

        user2 = User(
            tenant_id=tenant2.id,
            email="john@example.com",
            password_hash="hashed",
            name="John Smith",
            role=UserRole.TECHNICIAN,
            is_active=True
        )
        created2 = user_repo.create(user2)

        # Assert
        assert created1.id != created2.id
        assert created1.email == created2.email
        assert created1.tenant_id != created2.tenant_id

    def test_get_by_id_with_tenant(self, user_repo, test_tenant):
        """Test retrieving user by ID with tenant filtering."""
        # Arrange
        user = User(
            tenant_id=test_tenant.id,
            email="john@example.com",
            password_hash="hashed",
            name="John Doe",
            role=UserRole.TECHNICIAN,
            is_active=True
        )
        created = user_repo.create(user)

        # Act
        retrieved = user_repo.get_by_id(created.id, test_tenant.id)

        # Assert
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.email == "john@example.com"

    def test_get_by_id_wrong_tenant(self, user_repo, tenant_repo):
        """Test that getting user from wrong tenant returns None."""
        # Arrange
        tenant1 = tenant_repo.create(Tenant(name="Lab 1", is_active=True))
        tenant2 = tenant_repo.create(Tenant(name="Lab 2", is_active=True))

        user = User(
            tenant_id=tenant1.id,
            email="john@example.com",
            password_hash="hashed",
            name="John Doe",
            role=UserRole.TECHNICIAN,
            is_active=True
        )
        created = user_repo.create(user)

        # Act
        retrieved = user_repo.get_by_id(created.id, tenant2.id)

        # Assert
        assert retrieved is None  # Wrong tenant, so not found

    def test_get_by_email(self, user_repo, test_tenant):
        """Test retrieving user by email with tenant filtering."""
        # Arrange
        user = User(
            tenant_id=test_tenant.id,
            email="john@example.com",
            password_hash="hashed",
            name="John Doe",
            role=UserRole.TECHNICIAN,
            is_active=True
        )
        created = user_repo.create(user)

        # Act
        retrieved = user_repo.get_by_email("john@example.com", test_tenant.id)

        # Assert
        assert retrieved is not None
        assert retrieved.id == created.id

    def test_list_by_tenant(self, user_repo, tenant_repo):
        """Test listing users filtered by tenant."""
        # Arrange
        tenant1 = tenant_repo.create(Tenant(name="Lab 1", is_active=True))
        tenant2 = tenant_repo.create(Tenant(name="Lab 2", is_active=True))

        # Create users for tenant 1
        for i in range(3):
            user = User(
                tenant_id=tenant1.id,
                email=f"user{i}@lab1.com",
                password_hash="hashed",
                name=f"User {i}",
                role=UserRole.TECHNICIAN,
                is_active=True
            )
            user_repo.create(user)

        # Create users for tenant 2
        for i in range(2):
            user = User(
                tenant_id=tenant2.id,
                email=f"user{i}@lab2.com",
                password_hash="hashed",
                name=f"User {i}",
                role=UserRole.TECHNICIAN,
                is_active=True
            )
            user_repo.create(user)

        # Act
        tenant1_users = user_repo.list_by_tenant(tenant1.id)
        tenant2_users = user_repo.list_by_tenant(tenant2.id)

        # Assert
        assert len(tenant1_users) == 3
        assert len(tenant2_users) == 2
        assert all(u.tenant_id == tenant1.id for u in tenant1_users)
        assert all(u.tenant_id == tenant2.id for u in tenant2_users)

    def test_update_user(self, user_repo, test_tenant):
        """Test updating a user in database."""
        # Arrange
        user = User(
            tenant_id=test_tenant.id,
            email="john@example.com",
            password_hash="hashed",
            name="Old Name",
            role=UserRole.TECHNICIAN,
            is_active=True
        )
        created = user_repo.create(user)

        # Act
        created.name = "New Name"
        created.role = UserRole.ADMIN
        updated = user_repo.update(created)

        # Assert
        assert updated.name == "New Name"
        assert updated.role == UserRole.ADMIN

        # Verify persistence
        retrieved = user_repo.get_by_id(created.id, test_tenant.id)
        assert retrieved.name == "New Name"

    def test_delete_user(self, user_repo, test_tenant):
        """Test deleting a user from database."""
        # Arrange
        user = User(
            tenant_id=test_tenant.id,
            email="john@example.com",
            password_hash="hashed",
            name="John Doe",
            role=UserRole.TECHNICIAN,
            is_active=True
        )
        created = user_repo.create(user)

        # Act
        deleted = user_repo.delete(created.id, test_tenant.id)

        # Assert
        assert deleted is True

        # Verify deletion
        retrieved = user_repo.get_by_id(created.id, test_tenant.id)
        assert retrieved is None

    def test_delete_user_wrong_tenant(self, user_repo, tenant_repo):
        """Test deleting user from wrong tenant returns False."""
        # Arrange
        tenant1 = tenant_repo.create(Tenant(name="Lab 1", is_active=True))
        tenant2 = tenant_repo.create(Tenant(name="Lab 2", is_active=True))

        user = User(
            tenant_id=tenant1.id,
            email="john@example.com",
            password_hash="hashed",
            name="John Doe",
            role=UserRole.TECHNICIAN,
            is_active=True
        )
        created = user_repo.create(user)

        # Act
        deleted = user_repo.delete(created.id, tenant2.id)

        # Assert
        assert deleted is False

        # Verify user still exists in correct tenant
        retrieved = user_repo.get_by_id(created.id, tenant1.id)
        assert retrieved is not None

    def test_multi_tenant_isolation(self, user_repo, tenant_repo):
        """Test that multi-tenant isolation is enforced."""
        # Arrange
        tenant1 = tenant_repo.create(Tenant(name="Lab 1", is_active=True))
        tenant2 = tenant_repo.create(Tenant(name="Lab 2", is_active=True))

        user = User(
            tenant_id=tenant1.id,
            email="john@example.com",
            password_hash="hashed",
            name="John Doe",
            role=UserRole.TECHNICIAN,
            is_active=True
        )
        created = user_repo.create(user)

        # Act - try to access from different tenant
        retrieved_wrong_tenant = user_repo.get_by_id(created.id, tenant2.id)
        retrieved_correct_tenant = user_repo.get_by_id(created.id, tenant1.id)

        # Assert
        assert retrieved_wrong_tenant is None  # Cannot access from wrong tenant
        assert retrieved_correct_tenant is not None  # Can access from correct tenant
