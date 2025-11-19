"""Shared domain models across all services."""

# These models can be imported by multiple services
# to ensure consistency in data structures

from shared.models.order import Order, OrderStatus, OrderPriority

__all__ = [
    "Order",
    "OrderStatus",
    "OrderPriority",
]
