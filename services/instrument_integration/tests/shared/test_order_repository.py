"""Shared tests for OrderRepository - runs with both in-memory and PostgreSQL adapters."""

import pytest
from app.models import OrderStatus, OrderPriority
from app.exceptions import OrderNotFoundError, OrderAlreadyExistsError

TEST_TENANT_ID = "test-tenant-123"
TEST_SAMPLE_ID = "sample-123"


class TestOrderRepository:
    """Shared tests for Order Repository adapters."""

    def test_create_order(self, order_repository):
        """Test creating an order."""
        from app.models import Order
        
        order = Order(
            tenant_id=TEST_TENANT_ID,
            sample_id=TEST_SAMPLE_ID,
            external_lis_order_id="LIS-ORDER-001",
            patient_id="PAT-123",
            test_codes="GLU,WBC",
            priority=OrderPriority.ROUTINE,
            status=OrderStatus.PENDING
        )
        
        created = order_repository.create(order)
        
        assert created.id is not None
        assert created.external_lis_order_id == "LIS-ORDER-001"
        assert created.patient_id == "PAT-123"

    def test_create_duplicate_order_fails(self, order_repository):
        """Test that duplicate external_lis_order_id fails per tenant."""
        from app.models import Order
        
        order1 = Order(
            tenant_id=TEST_TENANT_ID,
            sample_id=TEST_SAMPLE_ID,
            external_lis_order_id="LIS-ORDER-001",
            patient_id="PAT-123",
            test_codes="GLU",
            priority=OrderPriority.ROUTINE
        )
        order_repository.create(order1)
        
        order2 = Order(
            tenant_id=TEST_TENANT_ID,
            sample_id=TEST_SAMPLE_ID,
            external_lis_order_id="LIS-ORDER-001",
            patient_id="PAT-124",
            test_codes="WBC",
            priority=OrderPriority.STAT
        )
        
        with pytest.raises(OrderAlreadyExistsError):
            order_repository.create(order2)

    def test_get_order_by_id(self, order_repository):
        """Test retrieving order by ID."""
        from app.models import Order
        
        order = Order(
            tenant_id=TEST_TENANT_ID,
            sample_id=TEST_SAMPLE_ID,
            external_lis_order_id="LIS-ORDER-002",
            patient_id="PAT-456",
            test_codes="HGB",
            priority=OrderPriority.CRITICAL
        )
        
        created = order_repository.create(order)
        retrieved = order_repository.get_by_id(created.id, TEST_TENANT_ID)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.external_lis_order_id == "LIS-ORDER-002"

    def test_get_order_not_found(self, order_repository):
        """Test retrieving non-existent order."""
        result = order_repository.get_by_id("nonexistent-id", TEST_TENANT_ID)
        assert result is None

    def test_list_orders_by_status(self, order_repository):
        """Test listing orders filtered by status."""
        from app.models import Order

        # Create pending order
        pending = Order(
            tenant_id=TEST_TENANT_ID,
            sample_id=TEST_SAMPLE_ID,
            external_lis_order_id="LIS-ORDER-PENDING",
            patient_id="PAT-P1",
            test_codes="GLU",
            status=OrderStatus.PENDING
        )

        # Create completed order
        completed = Order(
            tenant_id=TEST_TENANT_ID,
            sample_id=TEST_SAMPLE_ID,
            external_lis_order_id="LIS-ORDER-COMPLETE",
            patient_id="PAT-C1",
            test_codes="WBC",
            status=OrderStatus.COMPLETED
        )

        order_repository.create(pending)
        order_repository.create(completed)

        pending_orders = order_repository.search(
            tenant_id=TEST_TENANT_ID,
            status=OrderStatus.PENDING
        )

        # search() returns a list of results
        assert isinstance(pending_orders, list)
        assert len(pending_orders) == 1
        assert pending_orders[0].status == OrderStatus.PENDING

    def test_list_orders_by_sample(self, order_repository):
        """Test listing orders for a specific sample."""
        from app.models import Order

        sample_id = "sample-xyz"

        for i in range(2):
            order = Order(
                tenant_id=TEST_TENANT_ID,
                sample_id=sample_id,
                external_lis_order_id=f"LIS-ORDER-{i}",
                patient_id=f"PAT-{i}",
                test_codes="GLU"
            )
            order_repository.create(order)

        orders = order_repository.search(
            tenant_id=TEST_TENANT_ID,
            sample_id=sample_id
        )

        # search() returns a list, not a tuple
        assert isinstance(orders, list)
        assert len(orders) == 2
        assert all(o.sample_id == sample_id for o in orders)

    def test_update_order_status(self, order_repository):
        """Test updating order status."""
        from app.models import Order

        order = Order(
            tenant_id=TEST_TENANT_ID,
            sample_id=TEST_SAMPLE_ID,
            external_lis_order_id="LIS-ORDER-UPDATE",
            patient_id="PAT-U1",
            test_codes="HGB",
            status=OrderStatus.PENDING
        )

        created = order_repository.create(order)

        # Update status - returns the updated Order
        updated = order_repository.update_status(
            created.id,
            TEST_TENANT_ID,
            OrderStatus.IN_PROGRESS
        )

        assert updated.status == OrderStatus.IN_PROGRESS

        # Verify update persisted
        retrieved = order_repository.get_by_id(created.id, TEST_TENANT_ID)
        assert retrieved.status == OrderStatus.IN_PROGRESS

    def test_tenant_isolation(self, order_repository):
        """Test that orders are isolated by tenant."""
        from app.models import Order

        order1 = Order(
            tenant_id="tenant-1",
            sample_id="sample-1",
            external_lis_order_id="LIS-ORDER-T1",
            patient_id="PAT-T1",
            test_codes="GLU"
        )

        order2 = Order(
            tenant_id="tenant-2",
            sample_id="sample-2",
            external_lis_order_id="LIS-ORDER-T2",
            patient_id="PAT-T2",
            test_codes="WBC"
        )

        order_repository.create(order1)
        order_repository.create(order2)

        # search() returns a list of results
        orders_1 = order_repository.search(tenant_id="tenant-1")
        orders_2 = order_repository.search(tenant_id="tenant-2")

        assert isinstance(orders_1, list)
        assert isinstance(orders_2, list)
        assert len(orders_1) == 1
        assert len(orders_2) == 1
        assert orders_1[0].patient_id == "PAT-T1"
        assert orders_2[0].patient_id == "PAT-T2"
