"""Shared tests for InstrumentResultRepository - runs with both in-memory and PostgreSQL adapters."""

import pytest
from datetime import datetime, timedelta
from app.models import InstrumentResultStatus
from app.exceptions import InstrumentResultAlreadyExistsError

TEST_TENANT_ID = "test-tenant-123"
TEST_INSTRUMENT_ID = "instrument-123"


class TestInstrumentResultRepository:
    """Shared tests for InstrumentResult Repository adapters."""

    def test_create_result(self, instrument_result_repository):
        """Test creating an instrument result."""
        from app.models import InstrumentResult
        
        result = InstrumentResult(
            tenant_id=TEST_TENANT_ID,
            instrument_id=TEST_INSTRUMENT_ID,
            external_instrument_result_id="EXT-RESULT-001",
            test_code="GLU",
            test_name="Glucose",
            value="95",
            unit="mg/dL",
            reference_range_low=70.0,
            reference_range_high=100.0,
            collection_timestamp=datetime.utcnow()
        )
        
        created = instrument_result_repository.create(result)
        
        assert created.id is not None
        assert created.external_instrument_result_id == "EXT-RESULT-001"
        assert created.test_code == "GLU"

    def test_create_duplicate_result_fails(self, instrument_result_repository):
        """Test that duplicate results per tenant and instrument fail."""
        from app.models import InstrumentResult
        
        result1 = InstrumentResult(
            tenant_id=TEST_TENANT_ID,
            instrument_id=TEST_INSTRUMENT_ID,
            external_instrument_result_id="EXT-RESULT-DUP",
            test_code="GLU",
            test_name="Glucose",
            value="95",
            unit="mg/dL",
            collection_timestamp=datetime.utcnow()
        )
        instrument_result_repository.create(result1)
        
        result2 = InstrumentResult(
            tenant_id=TEST_TENANT_ID,
            instrument_id=TEST_INSTRUMENT_ID,
            external_instrument_result_id="EXT-RESULT-DUP",
            test_code="WBC",
            test_name="White Blood Cell",
            value="7.2",
            unit="K/uL",
            collection_timestamp=datetime.utcnow()
        )
        
        with pytest.raises(InstrumentResultAlreadyExistsError):
            instrument_result_repository.create(result2)

    def test_get_result_by_id(self, instrument_result_repository):
        """Test retrieving result by ID."""
        from app.models import InstrumentResult
        
        result = InstrumentResult(
            tenant_id=TEST_TENANT_ID,
            instrument_id=TEST_INSTRUMENT_ID,
            external_instrument_result_id="EXT-RESULT-GET",
            test_code="HGB",
            test_name="Hemoglobin",
            value="14.5",
            unit="g/dL",
            collection_timestamp=datetime.utcnow()
        )
        
        created = instrument_result_repository.create(result)
        retrieved = instrument_result_repository.get_by_id(created.id, TEST_TENANT_ID)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.test_code == "HGB"

    def test_get_result_by_external_id(self, instrument_result_repository):
        """Test retrieving result by external ID."""
        from app.models import InstrumentResult

        result = InstrumentResult(
            tenant_id=TEST_TENANT_ID,
            instrument_id=TEST_INSTRUMENT_ID,
            external_instrument_result_id="EXT-UNIQUE-123",
            test_code="PLT",
            test_name="Platelets",
            value="250",
            unit="K/uL",
            collection_timestamp=datetime.utcnow()
        )

        instrument_result_repository.create(result)

        # Parameters: external_id, instrument_id, tenant_id
        retrieved = instrument_result_repository.get_by_external_id(
            "EXT-UNIQUE-123",
            TEST_INSTRUMENT_ID,
            TEST_TENANT_ID
        )

        assert retrieved is not None
        assert retrieved.external_instrument_result_id == "EXT-UNIQUE-123"

    def test_search_results_by_status(self, instrument_result_repository):
        """Test searching results by status."""
        from app.models import InstrumentResult

        # Create results with different statuses
        for i, status in enumerate([InstrumentResultStatus.RECEIVED, InstrumentResultStatus.VALIDATED]):
            result = InstrumentResult(
                tenant_id=TEST_TENANT_ID,
                instrument_id=TEST_INSTRUMENT_ID,
                external_instrument_result_id=f"EXT-STATUS-{i}",
                test_code="GLU",
                test_name="Glucose",
                value=str(90 + i),
                unit="mg/dL",
                status=status,
                collection_timestamp=datetime.utcnow()
            )
            instrument_result_repository.create(result)

        # search() returns tuple (results, count)
        results, count = instrument_result_repository.search(
            tenant_id=TEST_TENANT_ID,
            status=InstrumentResultStatus.RECEIVED
        )

        assert count == 1
        assert len(results) == 1
        assert results[0].status == InstrumentResultStatus.RECEIVED

    def test_search_results_by_instrument(self, instrument_result_repository):
        """Test searching results by instrument."""
        from app.models import InstrumentResult

        for i in range(2):
            result = InstrumentResult(
                tenant_id=TEST_TENANT_ID,
                instrument_id=TEST_INSTRUMENT_ID,
                external_instrument_result_id=f"EXT-INST-{i}",
                test_code="GLU",
                test_name="Glucose",
                value=str(95 + i),
                unit="mg/dL",
                collection_timestamp=datetime.utcnow()
            )
            instrument_result_repository.create(result)

        # search() returns tuple (results, count)
        results, count = instrument_result_repository.search(
            tenant_id=TEST_TENANT_ID,
            instrument_id=TEST_INSTRUMENT_ID
        )

        assert count == 2
        assert len(results) == 2
        assert all(r.instrument_id == TEST_INSTRUMENT_ID for r in results)

    def test_update_result_status(self, instrument_result_repository):
        """Test updating result status."""
        from app.models import InstrumentResult
        
        result = InstrumentResult(
            tenant_id=TEST_TENANT_ID,
            instrument_id=TEST_INSTRUMENT_ID,
            external_instrument_result_id="EXT-UPDATE-STATUS",
            test_code="WBC",
            test_name="White Blood Cell",
            value="7.2",
            unit="K/uL",
            status=InstrumentResultStatus.RECEIVED,
            collection_timestamp=datetime.utcnow()
        )
        
        created = instrument_result_repository.create(result)
        created.status = InstrumentResultStatus.VALIDATED
        
        updated = instrument_result_repository.update(created)
        
        assert updated.status == InstrumentResultStatus.VALIDATED

    def test_tenant_isolation(self, instrument_result_repository):
        """Test that results are isolated by tenant."""
        from app.models import InstrumentResult

        result1 = InstrumentResult(
            tenant_id="tenant-1",
            instrument_id="inst-1",
            external_instrument_result_id="EXT-T1",
            test_code="GLU",
            test_name="Glucose",
            value="95",
            unit="mg/dL",
            collection_timestamp=datetime.utcnow()
        )

        result2 = InstrumentResult(
            tenant_id="tenant-2",
            instrument_id="inst-2",
            external_instrument_result_id="EXT-T2",
            test_code="WBC",
            test_name="White Blood Cell",
            value="7.2",
            unit="K/uL",
            collection_timestamp=datetime.utcnow()
        )

        instrument_result_repository.create(result1)
        instrument_result_repository.create(result2)

        # search() returns tuple (results, count)
        results_1, count_1 = instrument_result_repository.search(tenant_id="tenant-1")
        results_2, count_2 = instrument_result_repository.search(tenant_id="tenant-2")

        assert count_1 == 1
        assert count_2 == 1
        assert len(results_1) == 1
        assert len(results_2) == 1
        assert results_1[0].test_code == "GLU"
        assert results_2[0].test_code == "WBC"
