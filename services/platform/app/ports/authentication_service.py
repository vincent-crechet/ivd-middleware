"""Authentication service port."""

import abc
from typing import Optional
from datetime import datetime


class IAuthenticationService(abc.ABC):
    """
    Port: Abstract contract for authentication operations.

    Implementations handle JWT token generation and validation.
    """

    @abc.abstractmethod
    def create_access_token(
        self,
        user_id: str,
        tenant_id: str,
        role: str,
        expires_delta: Optional[int] = None
    ) -> str:
        """
        Create a JWT access token.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier (for multi-tenancy)
            role: User role (admin, technician, pathologist)
            expires_delta: Optional expiration time in seconds

        Returns:
            JWT token string
        """
        pass

    @abc.abstractmethod
    def verify_token(self, token: str) -> Optional[dict]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload if valid, None otherwise
        """
        pass
