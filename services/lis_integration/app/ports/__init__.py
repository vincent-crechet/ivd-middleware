"""Ports (abstract interfaces) for LIS Integration Service."""

from app.ports.sample_repository import ISampleRepository
from app.ports.result_repository import IResultRepository
from app.ports.lis_config_repository import ILISConfigRepository
from app.ports.order_repository import IOrderRepository
from app.ports.lis_adapter import ILISAdapter

__all__ = [
    "ISampleRepository",
    "IResultRepository",
    "ILISConfigRepository",
    "IOrderRepository",
    "ILISAdapter",
]
