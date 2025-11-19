"""In-memory implementation of order repository for testing."""

from typing import Optional
import uuid
import copy

from app.ports import IOrderRepository
from app.models import Order, OrderStatus
from app.exceptions import OrderNotFoundError


class InMemoryOrderRepository(IOrderRepository):
    """In-memory implementation of order repository for testing."""

    def __init__(self):
        """Initialize with empty storage."""
        self._orders: dict[str, Order] = {}

    def create(self, order: Order) -> Order:
        """Create a new order in memory."""
        if not order.tenant_id:
            raise ValueError("Order must have a tenant_id")
        if not order.sample_id:
            raise ValueError("Order must have a sample_id")

        if not order.id:
            order.id = str(uuid.uuid4())

        self._orders[order.id] = copy.deepcopy(order)
        return copy.deepcopy(self._orders[order.id])

    def get_by_id(self, order_id: str, tenant_id: str) -> Optional[Order]:
        """Retrieve order by ID, ensuring it belongs to tenant."""
        order = self._orders.get(order_id)
        if order and order.tenant_id == tenant_id:
            return copy.deepcopy(order)
        return None

    def get_by_external_id(self, external_lis_order_id: str, tenant_id: str) -> Optional[Order]:
        """Retrieve order by external LIS ID within tenant."""
        for order in self._orders.values():
            if order.external_lis_order_id == external_lis_order_id and order.tenant_id == tenant_id:
                return copy.deepcopy(order)
        return None

    def list_by_sample(self, sample_id: str, tenant_id: str) -> list[Order]:
        """List all orders for a specific sample."""
        orders = [o for o in self._orders.values()
                  if o.sample_id == sample_id and o.tenant_id == tenant_id]
        orders.sort(key=lambda o: o.created_at, reverse=True)
        return [copy.deepcopy(o) for o in orders]

    def list_by_tenant(
        self,
        tenant_id: str,
        status: Optional[OrderStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Order], int]:
        """List orders for a tenant with optional filtering."""
        orders = [o for o in self._orders.values() if o.tenant_id == tenant_id]

        if status:
            orders = [o for o in orders if o.status == status]

        orders.sort(key=lambda o: o.created_at, reverse=True)
        total = len(orders)
        paginated = orders[skip:skip + limit]

        return [copy.deepcopy(o) for o in paginated], total

    def update(self, order: Order) -> Order:
        """Update existing order."""
        if order.id not in self._orders:
            raise OrderNotFoundError(f"Order with id '{order.id}' not found")

        existing = self._orders[order.id]
        if existing.tenant_id != order.tenant_id:
            raise OrderNotFoundError(f"Order with id '{order.id}' not found")

        order.update_timestamp()
        self._orders[order.id] = copy.deepcopy(order)
        return copy.deepcopy(order)

    def update_status(self, order_id: str, tenant_id: str, status: OrderStatus) -> Order:
        """Update only the status of an order."""
        order = self.get_by_id(order_id, tenant_id)
        if not order:
            raise OrderNotFoundError(f"Order with id '{order_id}' not found")

        order.status = status
        order.update_timestamp()

        self._orders[order_id] = copy.deepcopy(order)
        return copy.deepcopy(order)

    def delete(self, order_id: str, tenant_id: str) -> bool:
        """Delete an order, ensuring it belongs to the tenant."""
        order = self._orders.get(order_id)
        if order and order.tenant_id == tenant_id:
            del self._orders[order_id]
            return True
        return False
