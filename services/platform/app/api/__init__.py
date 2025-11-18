"""API endpoints for Platform Service."""

from .tenants import router as tenants_router
from .users import router as users_router
from .auth import router as auth_router

__all__ = ["tenants_router", "users_router", "auth_router"]
