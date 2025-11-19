"""Adapters for LIS Integration Service."""

from app.adapters.postgres_sample_repository import PostgresSampleRepository
from app.adapters.postgres_result_repository import PostgresResultRepository
from app.adapters.postgres_lis_config_repository import PostgresLISConfigRepository
from app.adapters.postgres_order_repository import PostgresOrderRepository
from app.adapters.in_memory_sample_repository import InMemorySampleRepository
from app.adapters.in_memory_result_repository import InMemoryResultRepository
from app.adapters.in_memory_lis_config_repository import InMemoryLISConfigRepository
from app.adapters.in_memory_order_repository import InMemoryOrderRepository
from app.adapters.mock_lis_adapter import MockLISAdapter

__all__ = [
    "PostgresSampleRepository",
    "PostgresResultRepository",
    "PostgresLISConfigRepository",
    "PostgresOrderRepository",
    "InMemorySampleRepository",
    "InMemoryResultRepository",
    "InMemoryLISConfigRepository",
    "InMemoryOrderRepository",
    "MockLISAdapter",
]
