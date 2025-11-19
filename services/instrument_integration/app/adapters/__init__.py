"""Adapters for Instrument Integration Service."""

from app.adapters.postgres_instrument_repository import PostgresInstrumentRepository
from app.adapters.postgres_order_repository import PostgresOrderRepository
from app.adapters.postgres_instrument_query_repository import PostgresInstrumentQueryRepository
from app.adapters.postgres_instrument_result_repository import PostgresInstrumentResultRepository
from app.adapters.in_memory_instrument_repository import InMemoryInstrumentRepository
from app.adapters.in_memory_order_repository import InMemoryOrderRepository
from app.adapters.in_memory_instrument_query_repository import InMemoryInstrumentQueryRepository
from app.adapters.in_memory_instrument_result_repository import InMemoryInstrumentResultRepository

__all__ = [
    "PostgresInstrumentRepository",
    "PostgresOrderRepository",
    "PostgresInstrumentQueryRepository",
    "PostgresInstrumentResultRepository",
    "InMemoryInstrumentRepository",
    "InMemoryOrderRepository",
    "InMemoryInstrumentQueryRepository",
    "InMemoryInstrumentResultRepository",
]
"""Repository and adapter implementations."""

from app.adapters.in_memory_instrument_repository import InMemoryInstrumentRepository
from app.adapters.postgres_instrument_repository import PostgresInstrumentRepository
from app.adapters.in_memory_order_repository import InMemoryOrderRepository
from app.adapters.postgres_order_repository import PostgresOrderRepository
from app.adapters.in_memory_instrument_query_repository import InMemoryInstrumentQueryRepository
from app.adapters.postgres_instrument_query_repository import PostgresInstrumentQueryRepository
from app.adapters.in_memory_instrument_result_repository import InMemoryInstrumentResultRepository
from app.adapters.postgres_instrument_result_repository import PostgresInstrumentResultRepository
from app.adapters.mock_instrument_adapter import MockInstrumentAdapter

__all__ = [
    "InMemoryInstrumentRepository",
    "PostgresInstrumentRepository",
    "InMemoryOrderRepository",
    "PostgresOrderRepository",
    "InMemoryInstrumentQueryRepository",
    "PostgresInstrumentQueryRepository",
    "InMemoryInstrumentResultRepository",
    "PostgresInstrumentResultRepository",
    "MockInstrumentAdapter",
]
