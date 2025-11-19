"""PostgreSQL implementation of order repository."""

from sqlmodel import Session, select
from typing import Optional
import uuid

from app.ports import IOrderRepository
from app.models.order import Order, OrderStatus
from app.exceptions import OrderAlreadyExistsError, OrderNotFoundError


class PostgresOrderRepository(IOrderRepository):
    """PostgreSQL implementation of order repository with multi-tenant support."""

    def __init__(self, session: Session):
        """
        Initialize with database session.

        Args:
            session: SQLModel database session
        """
        self._session = session

    def create(self, order: Order) -> Order:
        """Create a new order in PostgreSQL."""
        # Validate required fields
        if not order.tenant_id:
            raise ValueError("Order must have a tenant_id")

        if not order.sample_id:
            raise ValueError("Order must have a sample_id")

        # Check for duplicate external_lis_order_id within tenant
        existing = self._session.exec(
            select(Order).where(
                Order.external_lis_order_id == order.external_lis_order_id,
                Order.tenant_id == order.tenant_id
            )
        ).first()

        if existing:
            raise OrderAlreadyExistsError(
                f"Order with external_lis_order_id '{order.external_lis_order_id}' already exists in tenant"
            )

        # Generate ID if not provided
        if not order.id:
            order.id = str(uuid.uuid4())

        self._session.add(order)
        self._session.commit()
        self._session.refresh(order)
        return order

    def get_by_id(self, order_id: str, tenant_id: str) -> Optional[Order]:
        """Retrieve order by ID, ensuring it belongs to tenant."""
        statement = select(Order).where(
            Order.id == order_id,
            Order.tenant_id == tenant_id
        )
        return self._session.exec(statement).first()

    def get_by_tenant(
        self,
        tenant_id: str,
        status: Optional[OrderStatus] = None,
        sample_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Order], int]:
        """List orders for a tenant with optional filtering."""
        # Build base query
        query = select(Order).where(Order.tenant_id == tenant_id)

        # Apply filters
        if status:
            query = query.where(Order.status == status)
        if sample_id:
            query = query.where(Order.sample_id == sample_id)

        # Get total count before pagination
        count_query = select(Order).where(Order.tenant_id == tenant_id)
        if status:
            count_query = count_query.where(Order.status == status)
        if sample_id:
            count_query = count_query.where(Order.sample_id == sample_id)

        total = len(self._session.exec(count_query).all())

        # Sort by created_at (newest first) and apply pagination
        query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)
        orders = list(self._session.exec(query).all())

        return orders, total

    def search(
        self,
        tenant_id: str,
        status: Optional[OrderStatus] = None,
        sample_id: Optional[str] = None
    ) -> list[Order]:
        """Search orders by criteria."""
        # Build query
        query = select(Order).where(Order.tenant_id == tenant_id)

        # Apply filters
        if status:
            query = query.where(Order.status == status)
        if sample_id:
            query = query.where(Order.sample_id == sample_id)

        # Sort by created_at (newest first)
        query = query.order_by(Order.created_at.desc())
        return list(self._session.exec(query).all())

    def update_status(self, order_id: str, tenant_id: str, status: OrderStatus) -> Order:
        """Update only the status of an order."""
        with self._session.no_autoflush:
            order = self.get_by_id(order_id, tenant_id)
            if not order:
                raise OrderNotFoundError(f"Order with id '{order_id}' not found")

            order.status = status
            order.update_timestamp()

        self._session.add(order)
        self._session.commit()
        self._session.refresh(order)
        return order

    def update(self, order: Order) -> Order:
        """Update existing order."""
        with self._session.no_autoflush:
            existing = self.get_by_id(order.id, order.tenant_id)
            if not existing:
                raise OrderNotFoundError(f"Order with id '{order.id}' not found")

            # Update fields
            existing.external_lis_order_id = order.external_lis_order_id
            existing.patient_id = order.patient_id
            existing.sample_id = order.sample_id
            existing.test_codes = order.test_codes
            existing.priority = order.priority
            existing.assigned_instrument_id = order.assigned_instrument_id
            existing.status = order.status
            existing.created_by = order.created_by
            existing.assigned_at = order.assigned_at
            existing.completed_at = order.completed_at
            existing.update_timestamp()

        self._session.add(existing)
        self._session.commit()
        self._session.refresh(existing)
        return existing

    def delete(self, order_id: str, tenant_id: str) -> bool:
        """Delete an order, ensuring it belongs to the tenant."""
        order = self.get_by_id(order_id, tenant_id)
        if not order:
            return False

        self._session.delete(order)
        self._session.commit()
        return True
