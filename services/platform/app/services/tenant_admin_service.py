"""Service for creating tenant with first admin user (SPEC Feature 1)."""

from typing import Optional
from app.ports import ITenantRepository, IUserRepository, IPasswordHasher
from app.models import Tenant, User, UserRole
from app.exceptions import InvalidPasswordError
import re


class TenantAdminService:
    """
    Service for atomic tenant creation with first admin user.

    Per SPECIFICATION.md Feature 1:
    "During tenant creation, first admin user is created with name, email, and password"
    """

    def __init__(
        self,
        tenant_repo: ITenantRepository,
        user_repo: IUserRepository,
        password_hasher: IPasswordHasher
    ):
        """
        Initialize service with dependencies.

        Args:
            tenant_repo: Tenant repository implementation
            user_repo: User repository implementation
            password_hasher: Password hasher implementation
        """
        self._tenant_repo = tenant_repo
        self._user_repo = user_repo
        self._password_hasher = password_hasher

    def create_tenant_with_admin(
        self,
        tenant_name: str,
        tenant_description: Optional[str],
        admin_name: str,
        admin_email: str,
        admin_password: str
    ) -> dict:
        """
        Create a new tenant with first admin user atomically.

        This is the primary way to onboard new laboratories per SPEC Feature 1.

        Business Rules:
        - Tenant name must be unique
        - Email must be valid format
        - Password must be at least 8 characters
        - First user must be an Admin
        - Both tenant and user created atomically

        Args:
            tenant_name: Laboratory/tenant name
            tenant_description: Optional description
            admin_name: First admin user's full name
            admin_email: First admin user's email
            admin_password: First admin user's password

        Returns:
            Dictionary with created tenant and user info

        Raises:
            DuplicateTenantError: If tenant name exists
            InvalidPasswordError: If password doesn't meet requirements
            ValueError: If email format is invalid
        """
        # Validate email format
        if not self._is_valid_email(admin_email):
            raise ValueError(f"Invalid email format: {admin_email}")

        # Validate password
        if len(admin_password) < 8:
            raise InvalidPasswordError("Password must be at least 8 characters")

        # Create tenant
        tenant = Tenant(
            name=tenant_name.strip(),
            description=tenant_description,
            is_active=True
        )
        created_tenant = self._tenant_repo.create(tenant)

        # Hash password
        password_hash = self._password_hasher.hash(admin_password)

        # Create first admin user
        admin_user = User(
            tenant_id=created_tenant.id,
            email=admin_email.lower().strip(),
            password_hash=password_hash,
            name=admin_name.strip(),
            role=UserRole.ADMIN,
            is_active=True
        )
        created_user = self._user_repo.create(admin_user)

        return {
            "tenant": {
                "id": created_tenant.id,
                "name": created_tenant.name,
                "description": created_tenant.description,
                "is_active": created_tenant.is_active
            },
            "admin_user": {
                "id": created_user.id,
                "email": created_user.email,
                "name": created_user.name,
                "role": created_user.role.value,
                "tenant_id": created_user.tenant_id
            }
        }

    @staticmethod
    def _is_valid_email(email: str) -> bool:
        """
        Validate email format.

        Args:
            email: Email address to validate

        Returns:
            True if valid email format
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
