"""Order domain model for test orders from LIS.

This module re-exports the canonical Order model from the shared package.
The Order model is owned by LIS Integration but used by both LIS Integration
and Instrument Integration services.
"""

# Re-export from shared package for backward compatibility
from shared.models.order import Order, OrderStatus, OrderPriority

__all__ = [
    "Order",
    "OrderStatus",
    "OrderPriority",
]
