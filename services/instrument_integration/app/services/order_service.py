"""Order business logic service."""

from typing import Optional
from datetime import datetime

from app.models import Order, OrderStatus, OrderPriority
from app.ports import IOrderRepository
from app.exceptions import (
    OrderNotFoundError,
    OrderAlreadyExistsError,
    InvalidOrderDataError,
)


class OrderService:
    """
    Service for managing test orders with business logic.

    Handles creation, retrieval, assignment, and status management of orders.
    Orders are created from LIS and assigned to instruments for execution.
    Depends only on IOrderRepository port.
    """

    def __init__(self, order_repo: IOrderRepository):
        """
        Initialize order service with repository.

        Args:
            order_repo: Order repository (injected port)
        """
        self._order_repo = order_repo

    def create_order(
        self,
        tenant_id: str,
        sample_id: str,
        external_lis_order_id: str,
        patient_id: str,
        test_codes: str,
        priority: OrderPriority = OrderPriority.ROUTINE
    ) -> Order:
        """
        Create a new order from LIS.

        Args:
            tenant_id: Tenant identifier
            sample_id: Sample identifier
            external_lis_order_id: External LIS order ID
            patient_id: Patient identifier
            test_codes: CSV or JSON list of test codes
            priority: Order priority (default: ROUTINE)

        Returns:
            Created order

        Raises:
            OrderAlreadyExistsError: If order with same external_lis_order_id exists
            InvalidOrderDataError: If data validation fails
        """
        # Validate test codes
        if not test_codes or not test_codes.strip():
            raise InvalidOrderDataError("Test codes cannot be empty")

        # Create order
        order = Order(
            tenant_id=tenant_id,
            sample_id=sample_id,
            external_lis_order_id=external_lis_order_id,
            patient_id=patient_id,
            test_codes=test_codes,
            priority=priority,
            status=OrderStatus.PENDING,
            created_by="lis"
        )

        # Persist via repository
        return self._order_repo.create(order)

    def get_order(self, tenant_id: str, order_id: str) -> Order:
        """
        Get an order by ID.

        Args:
            tenant_id: Tenant identifier (for isolation)
            order_id: Order identifier

        Returns:
            Order

        Raises:
            OrderNotFoundError: If order not found
        """
        order = self._order_repo.get_by_id(order_id, tenant_id)
        if not order:
            raise OrderNotFoundError(f"Order '{order_id}' not found")
        return order

    def list_orders(
        self,
        tenant_id: str,
        status: Optional[OrderStatus] = None,
        sample_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Order], int]:
        """
        List orders with optional filters.

        Args:
            tenant_id: Tenant identifier
            status: Optional order status filter
            sample_id: Optional sample ID filter
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            Tuple of (orders, total count)
        """
        return self._order_repo.get_by_tenant(
            tenant_id=tenant_id,
            status=status,
            sample_id=sample_id,
            skip=skip,
            limit=limit
        )

    def get_pending_orders_for_sample(
        self,
        tenant_id: str,
        sample_id: str
    ) -> list[Order]:
        """
        Get pending orders for a specific sample.

        This is used when instruments query for pending work.

        Args:
            tenant_id: Tenant identifier
            sample_id: Sample identifier

        Returns:
            List of pending orders
        """
        return self._order_repo.search(
            tenant_id=tenant_id,
            status=OrderStatus.PENDING,
            sample_id=sample_id
        )

    def assign_order_to_instrument(
        self,
        tenant_id: str,
        order_id: str,
        instrument_id: str
    ) -> Order:
        """
        Assign an order to an instrument.

        Only pending orders can be assigned.

        Args:
            tenant_id: Tenant identifier
            order_id: Order identifier
            instrument_id: Instrument identifier

        Returns:
            Updated order

        Raises:
            OrderNotFoundError: If order not found
            InvalidOrderDataError: If order is not in PENDING status
        """
        order = self.get_order(tenant_id, order_id)

        # Validate order status
        if order.status != OrderStatus.PENDING:
            raise InvalidOrderDataError(
                f"Cannot assign order with status '{order.status}'. "
                "Only PENDING orders can be assigned."
            )

        # Assign to instrument
        order.assigned_instrument_id = instrument_id
        order.assigned_at = datetime.utcnow()
        order.update_timestamp()

        return self._order_repo.update(order)

    def mark_order_in_progress(self, tenant_id: str, order_id: str) -> Order:
        """
        Mark an order as in progress.

        Args:
            tenant_id: Tenant identifier
            order_id: Order identifier

        Returns:
            Updated order

        Raises:
            OrderNotFoundError: If order not found
        """
        order = self.get_order(tenant_id, order_id)
        order.status = OrderStatus.IN_PROGRESS
        order.update_timestamp()

        return self._order_repo.update(order)

    def mark_order_completed(self, tenant_id: str, order_id: str) -> Order:
        """
        Mark an order as completed.

        Args:
            tenant_id: Tenant identifier
            order_id: Order identifier

        Returns:
            Updated order

        Raises:
            OrderNotFoundError: If order not found
        """
        order = self.get_order(tenant_id, order_id)
        order.status = OrderStatus.COMPLETED
        order.completed_at = datetime.utcnow()
        order.update_timestamp()

        return self._order_repo.update(order)

    def mark_order_failed(self, tenant_id: str, order_id: str) -> Order:
        """
        Mark an order as failed.

        Args:
            tenant_id: Tenant identifier
            order_id: Order identifier

        Returns:
            Updated order

        Raises:
            OrderNotFoundError: If order not found
        """
        order = self.get_order(tenant_id, order_id)
        order.status = OrderStatus.FAILED
        order.update_timestamp()

        return self._order_repo.update(order)

    def cancel_order(self, tenant_id: str, order_id: str) -> Order:
        """
        Cancel an order.

        Args:
            tenant_id: Tenant identifier
            order_id: Order identifier

        Returns:
            Updated order

        Raises:
            OrderNotFoundError: If order not found
        """
        order = self.get_order(tenant_id, order_id)
        order.status = OrderStatus.CANCELLED
        order.update_timestamp()

        return self._order_repo.update(order)
