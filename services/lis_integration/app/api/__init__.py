"""API routes for LIS Integration Service."""

from app.api.samples import samples_router
from app.api.results import results_router
from app.api.lis_config import lis_config_router

__all__ = ["samples_router", "results_router", "lis_config_router"]
