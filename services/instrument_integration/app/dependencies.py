"""Dependency injection setup."""

from functools import lru_cache
from sqlmodel import create_engine, Session, SQLModel
from sqlmodel.pool import StaticPool

from app.config import settings
from app.adapters import (
    InMemoryInstrumentRepository,
    InMemoryOrderRepository,
    InMemoryInstrumentQueryRepository,
    InMemoryInstrumentResultRepository,
    PostgresInstrumentRepository,
    PostgresOrderRepository,
    PostgresInstrumentQueryRepository,
    PostgresInstrumentResultRepository,
)
from app.services import (
    InstrumentService,
    OrderService,
    InstrumentQueryService,
    InstrumentResultService,
)


@lru_cache()
def get_db_engine():
    """Create database engine (cached)."""
    if settings.database_url.startswith("sqlite"):
        engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
    else:
        engine = create_engine(settings.database_url, echo=False)
    
    # Create tables
    SQLModel.metadata.create_all(engine)
    return engine


def get_db_session() -> Session:
    """Get database session."""
    engine = get_db_engine()
    with Session(engine) as session:
        yield session


def get_instrument_repository(session: Session = None):
    """Get instrument repository based on configuration."""
    if settings.use_real_database and session:
        return PostgresInstrumentRepository(session)
    return InMemoryInstrumentRepository()


def get_order_repository(session: Session = None):
    """Get order repository based on configuration."""
    if settings.use_real_database and session:
        return PostgresOrderRepository(session)
    return InMemoryOrderRepository()


def get_instrument_query_repository(session: Session = None):
    """Get instrument query repository based on configuration."""
    if settings.use_real_database and session:
        return PostgresInstrumentQueryRepository(session)
    return InMemoryInstrumentQueryRepository()


def get_instrument_result_repository(session: Session = None):
    """Get instrument result repository based on configuration."""
    if settings.use_real_database and session:
        return PostgresInstrumentResultRepository(session)
    return InMemoryInstrumentResultRepository()


def get_instrument_service() -> InstrumentService:
    """Create instrument service."""
    repo = get_instrument_repository()
    return InstrumentService(repo)


def get_order_service() -> OrderService:
    """Create order service."""
    repo = get_order_repository()
    return OrderService(repo)


def get_instrument_query_service() -> InstrumentQueryService:
    """Create instrument query service."""
    repo = get_instrument_query_repository()
    return InstrumentQueryService(repo)


def get_instrument_result_service() -> InstrumentResultService:
    """Create instrument result service."""
    repo = get_instrument_result_repository()
    return InstrumentResultService(repo)
