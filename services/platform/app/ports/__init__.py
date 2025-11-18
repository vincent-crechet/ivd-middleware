"""Abstract ports (interfaces) for Platform Service."""

from .tenant_repository import ITenantRepository
from .user_repository import IUserRepository
from .password_hasher import IPasswordHasher
from .authentication_service import IAuthenticationService

__all__ = [
    "ITenantRepository",
    "IUserRepository",
    "IPasswordHasher",
    "IAuthenticationService",
]
