"""Order repository port."""

import abc
from typing import Optional
from app.models import Order, OrderStatus


class IOrderRepository(abc.ABC):
    """
    Port: Abstract contract for order data persistence with multi-tenant support.

    Orders represent test orders from LIS that instruments will execute.
    All queries automatically filter by tenant_id to ensure data isolation.
    """

    @abc.abstractmethod
    def create(self, order: Order) -> Order:
        """
        Create a new order.

        Args:
            order: Order entity to create (must have tenant_id and sample_id set)

        Returns:
            Created order with generated ID

        Raises:
            ValueError: If required fields are missing
        """
        pass

    @abc.abstractmethod
    def get_by_id(self, order_id: str, tenant_id: str) -> Optional[Order]:
        """
        Retrieve an order by ID, ensuring it belongs to the tenant.

        Args:
            order_id: Unique order identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            Order if found and belongs to tenant, None otherwise
        """
        pass

    @abc.abstractmethod
    def get_by_external_id(self, external_lis_order_id: str, tenant_id: str) -> Optional[Order]:
        """
        Retrieve an order by external LIS ID within a tenant.

        Args:
            external_lis_order_id: External LIS order identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            Order if found in tenant, None otherwise
        """
        pass

    @abc.abstractmethod
    def list_by_sample(self, sample_id: str, tenant_id: str) -> list[Order]:
        """
        List all orders for a specific sample.

        Args:
            sample_id: Sample identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            List of orders for the sample
        """
        pass

    @abc.abstractmethod
    def list_by_tenant(
        self,
        tenant_id: str,
        status: Optional[OrderStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Order], int]:
        """
        List orders for a tenant with optional filtering.

        Args:
            tenant_id: Tenant identifier
            status: Optional order status filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of orders, total count)
        """
        pass

    @abc.abstractmethod
    def update(self, order: Order) -> Order:
        """
        Update an existing order.

        Args:
            order: Order with updated fields

        Returns:
            Updated order

        Raises:
            OrderNotFoundError: If order doesn't exist
        """
        pass

    @abc.abstractmethod
    def update_status(self, order_id: str, tenant_id: str, status: OrderStatus) -> Order:
        """
        Update only the status of an order.

        Args:
            order_id: Order identifier
            tenant_id: Tenant identifier
            status: New order status

        Returns:
            Updated order

        Raises:
            OrderNotFoundError: If order doesn't exist
        """
        pass

    @abc.abstractmethod
    def delete(self, order_id: str, tenant_id: str) -> bool:
        """
        Delete an order, ensuring it belongs to the tenant.

        Args:
            order_id: ID of order to delete
            tenant_id: Tenant identifier for isolation

        Returns:
            True if deleted, False if not found
        """
        pass
