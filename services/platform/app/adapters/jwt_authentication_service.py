"""JWT implementation of authentication service."""

from datetime import datetime, timedelta
from typing import Optional
import jwt

from app.ports import IAuthenticationService


class JWTAuthenticationService(IAuthenticationService):
    """JWT implementation for token-based authentication."""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        """
        Initialize JWT service.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm (default: HS256)
        """
        self._secret_key = secret_key
        self._algorithm = algorithm

    def create_access_token(
        self,
        user_id: str,
        tenant_id: str,
        role: str,
        expires_delta: Optional[int] = None
    ) -> str:
        """
        Create a JWT access token with tenant context.

        Args:
            user_id: User identifier
            tenant_id: Tenant identifier (for multi-tenancy)
            role: User role (admin, technician, pathologist)
            expires_delta: Optional expiration time in seconds (default: 8 hours)

        Returns:
            JWT token string
        """
        if expires_delta is None:
            expires_delta = 28800  # 8 hours

        expire = datetime.utcnow() + timedelta(seconds=expires_delta)

        payload = {
            "sub": user_id,
            "tenant_id": tenant_id,
            "role": role,
            "exp": expire,
            "iat": datetime.utcnow()
        }

        token = jwt.encode(payload, self._secret_key, algorithm=self._algorithm)
        return token

    def verify_token(self, token: str) -> Optional[dict]:
        """
        Verify and decode a JWT token.

        Args:
            token: JWT token string

        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
