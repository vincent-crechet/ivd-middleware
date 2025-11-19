"""Shared tests for InstrumentRepository - runs with both in-memory and PostgreSQL adapters."""

import pytest
from app.models import InstrumentType, InstrumentStatus
from app.exceptions import InstrumentNotFoundError, InstrumentAlreadyExistsError

TEST_TENANT_ID = "test-tenant-123"


class TestInstrumentRepository:
    """Shared tests for Instrument Repository adapters."""

    def test_create_instrument(self, instrument_repository):
        """Test creating an instrument."""
        from app.models import Instrument
        
        instrument = Instrument(
            tenant_id=TEST_TENANT_ID,
            name="Analyzer-1",
            instrument_type=InstrumentType.CHEMISTRY,
            api_token="test-token-12345"
        )
        
        created = instrument_repository.create(instrument)
        
        assert created.id is not None
        assert created.name == "Analyzer-1"
        assert created.instrument_type == InstrumentType.CHEMISTRY
        assert created.api_token == "test-token-12345"

    def test_create_duplicate_instrument_fails(self, instrument_repository):
        """Test that duplicate instrument names per tenant fail."""
        from app.models import Instrument
        
        instrument1 = Instrument(
            tenant_id=TEST_TENANT_ID,
            name="Analyzer-1",
            instrument_type=InstrumentType.CHEMISTRY,
            api_token="token-1"
        )
        instrument_repository.create(instrument1)
        
        instrument2 = Instrument(
            tenant_id=TEST_TENANT_ID,
            name="Analyzer-1",
            instrument_type=InstrumentType.HEMATOLOGY,
            api_token="token-2"
        )
        
        with pytest.raises(InstrumentAlreadyExistsError):
            instrument_repository.create(instrument2)

    def test_get_instrument_by_id(self, instrument_repository):
        """Test retrieving instrument by ID."""
        from app.models import Instrument
        
        instrument = Instrument(
            tenant_id=TEST_TENANT_ID,
            name="Test Analyzer",
            instrument_type=InstrumentType.IMMUNOASSAY,
            api_token="test-token"
        )
        
        created = instrument_repository.create(instrument)
        retrieved = instrument_repository.get_by_id(created.id, TEST_TENANT_ID)
        
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.name == created.name

    def test_get_instrument_not_found(self, instrument_repository):
        """Test retrieving non-existent instrument."""
        result = instrument_repository.get_by_id("nonexistent-id", TEST_TENANT_ID)
        assert result is None

    def test_get_instrument_by_api_token(self, instrument_repository):
        """Test retrieving instrument by API token."""
        from app.models import Instrument
        
        instrument = Instrument(
            tenant_id=TEST_TENANT_ID,
            name="Token Test",
            instrument_type=InstrumentType.URINALYSIS,
            api_token="unique-token-12345"
        )
        
        instrument_repository.create(instrument)
        retrieved = instrument_repository.get_by_api_token("unique-token-12345")
        
        assert retrieved is not None
        assert retrieved.api_token == "unique-token-12345"

    def test_get_instruments_by_tenant(self, instrument_repository):
        """Test listing instruments for a tenant."""
        from app.models import Instrument
        
        for i in range(3):
            instrument = Instrument(
                tenant_id=TEST_TENANT_ID,
                name=f"Analyzer-{i}",
                instrument_type=InstrumentType.CHEMISTRY,
                api_token=f"token-{i}"
            )
            instrument_repository.create(instrument)
        
        instruments, count = instrument_repository.get_by_tenant(TEST_TENANT_ID)
        
        assert count == 3
        assert len(instruments) == 3

    def test_tenant_isolation(self, instrument_repository):
        """Test that instruments are isolated by tenant."""
        from app.models import Instrument
        
        instrument1 = Instrument(
            tenant_id="tenant-1",
            name="Analyzer",
            instrument_type=InstrumentType.HEMATOLOGY,
            api_token="token-1"
        )
        
        instrument2 = Instrument(
            tenant_id="tenant-2",
            name="Analyzer",
            instrument_type=InstrumentType.CHEMISTRY,
            api_token="token-2"
        )
        
        instrument_repository.create(instrument1)
        instrument_repository.create(instrument2)
        
        instruments_1, count_1 = instrument_repository.get_by_tenant("tenant-1")
        instruments_2, count_2 = instrument_repository.get_by_tenant("tenant-2")
        
        assert count_1 == 1
        assert count_2 == 1
        assert instruments_1[0].name == "Analyzer"
        assert instruments_2[0].name == "Analyzer"

    def test_update_instrument(self, instrument_repository):
        """Test updating an instrument."""
        from app.models import Instrument
        
        instrument = Instrument(
            tenant_id=TEST_TENANT_ID,
            name="Original Name",
            instrument_type=InstrumentType.CHEMISTRY,
            api_token="test-token",
            status=InstrumentStatus.INACTIVE
        )
        
        created = instrument_repository.create(instrument)
        created.name = "Updated Name"
        created.status = InstrumentStatus.ACTIVE
        
        updated = instrument_repository.update(created)
        
        assert updated.name == "Updated Name"
        assert updated.status == InstrumentStatus.ACTIVE

    def test_delete_instrument(self, instrument_repository):
        """Test deleting an instrument."""
        from app.models import Instrument
        
        instrument = Instrument(
            tenant_id=TEST_TENANT_ID,
            name="To Delete",
            instrument_type=InstrumentType.URINALYSIS,
            api_token="test-token"
        )
        
        created = instrument_repository.create(instrument)
        result = instrument_repository.delete(created.id, TEST_TENANT_ID)
        
        assert result is True
        
        # Verify deletion
        retrieved = instrument_repository.get_by_id(created.id, TEST_TENANT_ID)
        assert retrieved is None
