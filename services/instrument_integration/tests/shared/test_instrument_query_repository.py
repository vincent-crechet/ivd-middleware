"""Shared tests for InstrumentQueryRepository - runs with both in-memory and PostgreSQL adapters."""

from datetime import datetime, timedelta
from app.models import QueryResponseStatus


TEST_TENANT_ID = "test-tenant-123"
TEST_INSTRUMENT_ID = "instrument-123"


class TestInstrumentQueryRepository:
    """Shared tests for InstrumentQuery Repository adapters."""

    def test_create_query(self, instrument_query_repository):
        """Test creating an instrument query audit log entry."""
        from app.models import InstrumentQuery

        query = InstrumentQuery(
            tenant_id=TEST_TENANT_ID,
            instrument_id=TEST_INSTRUMENT_ID,
            query_patient_id="PAT-123",
            query_sample_barcode="SAMPLE-001",
            query_timestamp=datetime.utcnow(),
            response_timestamp=datetime.utcnow(),
            response_time_ms=150,
            orders_returned_count=2,
            response_status=QueryResponseStatus.SUCCESS
        )

        created = instrument_query_repository.create(query)

        assert created.id is not None
        assert created.tenant_id == TEST_TENANT_ID
        assert created.instrument_id == TEST_INSTRUMENT_ID
        assert created.orders_returned_count == 2
        assert created.response_status == QueryResponseStatus.SUCCESS

    def test_create_query_with_error(self, instrument_query_repository):
        """Test creating a query with error response."""
        from app.models import InstrumentQuery

        query = InstrumentQuery(
            tenant_id=TEST_TENANT_ID,
            instrument_id=TEST_INSTRUMENT_ID,
            query_timestamp=datetime.utcnow(),
            response_timestamp=datetime.utcnow(),
            response_time_ms=500,
            response_status=QueryResponseStatus.TIMEOUT,
            error_reason="Query timeout after 5 seconds"
        )

        created = instrument_query_repository.create(query)

        assert created.response_status == QueryResponseStatus.TIMEOUT
        assert created.error_reason == "Query timeout after 5 seconds"

    def test_get_by_instrument(self, instrument_query_repository):
        """Test retrieving queries for a specific instrument."""
        from app.models import InstrumentQuery

        now = datetime.utcnow()
        for i in range(3):
            query = InstrumentQuery(
                tenant_id=TEST_TENANT_ID,
                instrument_id=TEST_INSTRUMENT_ID,
                query_timestamp=now + timedelta(seconds=i),
                response_timestamp=now + timedelta(seconds=i, milliseconds=100),
                response_time_ms=100,
                orders_returned_count=i
            )
            instrument_query_repository.create(query)

        queries, count = instrument_query_repository.get_by_instrument(
            instrument_id=TEST_INSTRUMENT_ID,
            tenant_id=TEST_TENANT_ID
        )

        assert len(queries) == 3
        assert count == 3
        assert all(q.instrument_id == TEST_INSTRUMENT_ID for q in queries)

    def test_get_by_instrument_with_pagination(self, instrument_query_repository):
        """Test pagination when retrieving queries."""
        from app.models import InstrumentQuery

        now = datetime.utcnow()
        for i in range(5):
            query = InstrumentQuery(
                tenant_id=TEST_TENANT_ID,
                instrument_id=TEST_INSTRUMENT_ID,
                query_timestamp=now + timedelta(seconds=i),
                response_timestamp=now + timedelta(seconds=i, milliseconds=100),
                response_time_ms=100
            )
            instrument_query_repository.create(query)

        # Get first 2 records
        page1, total = instrument_query_repository.get_by_instrument(
            instrument_id=TEST_INSTRUMENT_ID,
            tenant_id=TEST_TENANT_ID,
            skip=0,
            limit=2
        )

        # Get next 2 records
        page2, _ = instrument_query_repository.get_by_instrument(
            instrument_id=TEST_INSTRUMENT_ID,
            tenant_id=TEST_TENANT_ID,
            skip=2,
            limit=2
        )

        assert len(page1) == 2
        assert len(page2) == 2
        assert total == 5
        # Verify different records
        assert page1[0].id != page2[0].id

    def test_search_queries_by_date_range(self, instrument_query_repository):
        """Test searching queries by date range."""
        from app.models import InstrumentQuery

        now = datetime.utcnow()

        # Create query before range
        query1 = InstrumentQuery(
            tenant_id=TEST_TENANT_ID,
            instrument_id=TEST_INSTRUMENT_ID,
            query_timestamp=now - timedelta(days=2),
            response_timestamp=now - timedelta(days=2),
            response_time_ms=100
        )
        instrument_query_repository.create(query1)

        # Create query in range
        query2 = InstrumentQuery(
            tenant_id=TEST_TENANT_ID,
            instrument_id=TEST_INSTRUMENT_ID,
            query_timestamp=now - timedelta(hours=1),
            response_timestamp=now - timedelta(hours=1),
            response_time_ms=100
        )
        instrument_query_repository.create(query2)

        # Create query after range
        query3 = InstrumentQuery(
            tenant_id=TEST_TENANT_ID,
            instrument_id=TEST_INSTRUMENT_ID,
            query_timestamp=now + timedelta(days=1),
            response_timestamp=now + timedelta(days=1),
            response_time_ms=100
        )
        instrument_query_repository.create(query3)

        # Search for queries in range
        results, count = instrument_query_repository.search(
            tenant_id=TEST_TENANT_ID,
            start_date=now - timedelta(hours=2),
            end_date=now
        )

        assert count == 1
        assert len(results) == 1
        assert results[0].id == query2.id

    def test_search_queries_by_instrument(self, instrument_query_repository):
        """Test searching queries filtered by instrument."""
        from app.models import InstrumentQuery

        now = datetime.utcnow()

        # Create queries for instrument 1
        for i in range(2):
            query = InstrumentQuery(
                tenant_id=TEST_TENANT_ID,
                instrument_id="instrument-1",
                query_timestamp=now + timedelta(seconds=i),
                response_timestamp=now + timedelta(seconds=i),
                response_time_ms=100
            )
            instrument_query_repository.create(query)

        # Create queries for instrument 2
        for i in range(3):
            query = InstrumentQuery(
                tenant_id=TEST_TENANT_ID,
                instrument_id="instrument-2",
                query_timestamp=now + timedelta(seconds=i),
                response_timestamp=now + timedelta(seconds=i),
                response_time_ms=100
            )
            instrument_query_repository.create(query)

        # Search for instrument-1 only
        results, count = instrument_query_repository.search(
            tenant_id=TEST_TENANT_ID,
            instrument_id="instrument-1"
        )

        assert count == 2
        assert len(results) == 2
        assert all(q.instrument_id == "instrument-1" for q in results)

    def test_search_with_all_filters(self, instrument_query_repository):
        """Test searching with combined date range and instrument filters."""
        from app.models import InstrumentQuery

        now = datetime.utcnow()

        # Create query outside date range for instrument 1
        q1 = InstrumentQuery(
            tenant_id=TEST_TENANT_ID,
            instrument_id="instrument-1",
            query_timestamp=now - timedelta(days=2),
            response_timestamp=now - timedelta(days=2),
            response_time_ms=100
        )
        instrument_query_repository.create(q1)

        # Create query in range for instrument 1
        q2 = InstrumentQuery(
            tenant_id=TEST_TENANT_ID,
            instrument_id="instrument-1",
            query_timestamp=now - timedelta(hours=1),
            response_timestamp=now - timedelta(hours=1),
            response_time_ms=100
        )
        instrument_query_repository.create(q2)

        # Create query in range for instrument 2
        q3 = InstrumentQuery(
            tenant_id=TEST_TENANT_ID,
            instrument_id="instrument-2",
            query_timestamp=now - timedelta(hours=1),
            response_timestamp=now - timedelta(hours=1),
            response_time_ms=100
        )
        instrument_query_repository.create(q3)

        # Search with both filters
        results, count = instrument_query_repository.search(
            tenant_id=TEST_TENANT_ID,
            instrument_id="instrument-1",
            start_date=now - timedelta(hours=2),
            end_date=now
        )

        assert count == 1
        assert len(results) == 1
        assert results[0].id == q2.id

    def test_tenant_isolation(self, instrument_query_repository):
        """Test that queries are isolated by tenant."""
        from app.models import InstrumentQuery

        now = datetime.utcnow()

        # Create query for tenant-1
        q1 = InstrumentQuery(
            tenant_id="tenant-1",
            instrument_id="inst-1",
            query_timestamp=now,
            response_timestamp=now,
            response_time_ms=100,
            orders_returned_count=5
        )
        instrument_query_repository.create(q1)

        # Create query for tenant-2
        q2 = InstrumentQuery(
            tenant_id="tenant-2",
            instrument_id="inst-2",
            query_timestamp=now,
            response_timestamp=now,
            response_time_ms=200,
            orders_returned_count=3
        )
        instrument_query_repository.create(q2)

        # Search for tenant-1
        results_1, count_1 = instrument_query_repository.search(tenant_id="tenant-1")

        # Search for tenant-2
        results_2, count_2 = instrument_query_repository.search(tenant_id="tenant-2")

        assert count_1 == 1
        assert count_2 == 1
        assert results_1[0].orders_returned_count == 5
        assert results_2[0].orders_returned_count == 3
