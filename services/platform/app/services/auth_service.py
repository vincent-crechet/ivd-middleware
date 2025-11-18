"""Authentication service."""

from typing import Optional
from datetime import datetime

from app.ports import IUserRepository, IPasswordHasher, IAuthenticationService
from app.exceptions import InvalidCredentialsError, UserNotFoundError


class AuthService:
    """
    Service for authentication operations.

    Depends on IUserRepository, IPasswordHasher, and IAuthenticationService.
    """

    def __init__(
        self,
        user_repo: IUserRepository,
        password_hasher: IPasswordHasher,
        auth_service: IAuthenticationService
    ):
        """
        Initialize service with dependencies.

        Args:
            user_repo: User repository implementation
            password_hasher: Password hasher implementation
            auth_service: Authentication service implementation
        """
        self._user_repo = user_repo
        self._password_hasher = password_hasher
        self._auth_service = auth_service

    def login(self, email: str, password: str, tenant_id: str) -> dict:
        """
        Authenticate user and generate access token.

        Args:
            email: User email
            password: Plain text password
            tenant_id: Tenant identifier

        Returns:
            Dictionary with access_token and user info

        Raises:
            InvalidCredentialsError: If credentials are invalid
        """
        # Get user by email within tenant
        user = self._user_repo.get_by_email(email.lower(), tenant_id)
        if not user:
            raise InvalidCredentialsError("Invalid email or password")

        # Check if user is active
        if not user.is_active:
            raise InvalidCredentialsError("User account is inactive")

        # Verify password
        if not self._password_hasher.verify(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")

        # Update last login
        user.last_login = datetime.utcnow()
        self._user_repo.update(user)

        # Generate access token with tenant context
        access_token = self._auth_service.create_access_token(
            user_id=user.id,
            tenant_id=user.tenant_id,
            role=user.role.value
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role.value,
                "tenant_id": user.tenant_id
            }
        }

    def verify_token(self, token: str) -> Optional[dict]:
        """
        Verify and decode an access token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload if valid, None otherwise
        """
        return self._auth_service.verify_token(token)

    def get_current_user(self, token: str) -> dict:
        """
        Get current user information from token.

        Args:
            token: JWT token string

        Returns:
            User information

        Raises:
            InvalidCredentialsError: If token is invalid
        """
        payload = self.verify_token(token)
        if not payload:
            raise InvalidCredentialsError("Invalid or expired token")

        user_id = payload.get("sub")
        tenant_id = payload.get("tenant_id")

        user = self._user_repo.get_by_id(user_id, tenant_id)
        if not user:
            raise InvalidCredentialsError("User not found")

        return {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "tenant_id": user.tenant_id
        }
