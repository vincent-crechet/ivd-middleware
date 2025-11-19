"""Tests for InstrumentService."""

import pytest
from app.models import InstrumentType, InstrumentStatus
from app.exceptions import InstrumentNotFoundError, InstrumentAlreadyExistsError

TEST_TENANT_ID = "test-tenant-123"


class TestInstrumentServiceCreateInstrument:
    """Tests for creating instruments."""

    def test_create_instrument_success(self, instrument_service):
        """Test successful instrument creation."""
        instrument = instrument_service.create_instrument(
            tenant_id=TEST_TENANT_ID,
            name="Hematology Analyzer",
            instrument_type=InstrumentType.HEMATOLOGY
        )

        assert instrument.id is not None
        assert instrument.name == "Hematology Analyzer"
        assert instrument.instrument_type == InstrumentType.HEMATOLOGY
        assert instrument.api_token is not None
        assert instrument.status == InstrumentStatus.INACTIVE

    def test_create_instrument_with_custom_token(self, instrument_service):
        """Test creating instrument with custom API token."""
        custom_token = "my-custom-token-12345"
        instrument = instrument_service.create_instrument(
            tenant_id=TEST_TENANT_ID,
            name="Chemistry Analyzer",
            instrument_type=InstrumentType.CHEMISTRY,
            api_token=custom_token
        )

        assert instrument.api_token == custom_token

    def test_create_duplicate_instrument_fails(self, instrument_service):
        """Test that duplicate instrument names fail."""
        instrument_service.create_instrument(
            tenant_id=TEST_TENANT_ID,
            name="Analyzer-1",
            instrument_type=InstrumentType.HEMATOLOGY
        )

        with pytest.raises(InstrumentAlreadyExistsError):
            instrument_service.create_instrument(
                tenant_id=TEST_TENANT_ID,
                name="Analyzer-1",
                instrument_type=InstrumentType.CHEMISTRY
            )

    def test_create_instrument_different_tenant_different_name(self, instrument_service):
        """Test creating instruments with same name in different tenants."""
        instrument1 = instrument_service.create_instrument(
            tenant_id="tenant-1",
            name="Analyzer",
            instrument_type=InstrumentType.HEMATOLOGY
        )

        instrument2 = instrument_service.create_instrument(
            tenant_id="tenant-2",
            name="Analyzer",
            instrument_type=InstrumentType.CHEMISTRY
        )

        assert instrument1.id != instrument2.id
        assert instrument1.tenant_id == "tenant-1"
        assert instrument2.tenant_id == "tenant-2"


class TestInstrumentServiceGetInstrument:
    """Tests for retrieving instruments."""

    def test_get_instrument_success(self, instrument_service):
        """Test successful instrument retrieval."""
        created = instrument_service.create_instrument(
            tenant_id=TEST_TENANT_ID,
            name="Test Analyzer",
            instrument_type=InstrumentType.CHEMISTRY
        )

        retrieved = instrument_service.get_instrument(
            tenant_id=TEST_TENANT_ID,
            instrument_id=created.id
        )

        assert retrieved.id == created.id
        assert retrieved.name == created.name

    def test_get_instrument_not_found(self, instrument_service):
        """Test retrieval of non-existent instrument."""
        with pytest.raises(InstrumentNotFoundError):
            instrument_service.get_instrument(
                tenant_id=TEST_TENANT_ID,
                instrument_id="nonexistent-id"
            )

    def test_get_instrument_by_api_token(self, instrument_service):
        """Test retrieving instrument by API token."""
        created = instrument_service.create_instrument(
            tenant_id=TEST_TENANT_ID,
            name="Token Test Analyzer",
            instrument_type=InstrumentType.IMMUNOASSAY
        )

        retrieved = instrument_service.get_by_api_token(created.api_token)

        assert retrieved.id == created.id
        assert retrieved.api_token == created.api_token


class TestInstrumentServiceUpdateInstrument:
    """Tests for updating instruments."""

    def test_update_instrument_name(self, instrument_service):
        """Test updating instrument name."""
        created = instrument_service.create_instrument(
            tenant_id=TEST_TENANT_ID,
            name="Original Name",
            instrument_type=InstrumentType.CHEMISTRY
        )

        updated = instrument_service.update_instrument(
            tenant_id=TEST_TENANT_ID,
            instrument_id=created.id,
            name="Updated Name"
        )

        assert updated.name == "Updated Name"

    def test_update_instrument_status(self, instrument_service):
        """Test updating instrument status."""
        created = instrument_service.create_instrument(
            tenant_id=TEST_TENANT_ID,
            name="Test Analyzer",
            instrument_type=InstrumentType.HEMATOLOGY
        )

        updated = instrument_service.update_instrument(
            tenant_id=TEST_TENANT_ID,
            instrument_id=created.id,
            status=InstrumentStatus.ACTIVE
        )

        assert updated.status == InstrumentStatus.ACTIVE


class TestInstrumentServiceSuccessTracking:
    """Tests for tracking instrument success/failure."""

    def test_record_successful_query(self, instrument_service):
        """Test recording successful query."""
        created = instrument_service.create_instrument(
            tenant_id=TEST_TENANT_ID,
            name="Test Analyzer",
            instrument_type=InstrumentType.CHEMISTRY
        )

        instrument_service.record_successful_query(
            tenant_id=TEST_TENANT_ID,
            instrument_id=created.id
        )

        updated = instrument_service.get_instrument(
            tenant_id=TEST_TENANT_ID,
            instrument_id=created.id
        )

        assert updated.last_successful_query_at is not None
        assert updated.connection_failure_count == 0

    def test_regenerate_api_token(self, instrument_service):
        """Test regenerating API token."""
        created = instrument_service.create_instrument(
            tenant_id=TEST_TENANT_ID,
            name="Test Analyzer",
            instrument_type=InstrumentType.HEMATOLOGY
        )

        original_token = created.api_token

        updated = instrument_service.regenerate_api_token(
            tenant_id=TEST_TENANT_ID,
            instrument_id=created.id
        )

        assert updated.api_token != original_token
        assert updated.api_token is not None
