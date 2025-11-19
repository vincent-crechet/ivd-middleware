"""Tests for SampleService (shared tests run against in-memory and PostgreSQL)."""

import pytest
from datetime import datetime, timedelta

from app.models import SampleStatus
from app.exceptions import SampleNotFoundError, InvalidSampleDataError, DuplicateSampleError


TEST_TENANT_ID = "test-tenant-123"


class TestSampleServiceCreateSample:
    """Tests for creating samples."""

    def test_create_sample_success(self, sample_service):
        """Test successful sample creation."""
        now = datetime.utcnow()

        sample = sample_service.create_sample(
            tenant_id=TEST_TENANT_ID,
            external_lis_id="LIS-SAMPLE-001",
            patient_id="PAT001",
            specimen_type="blood",
            collection_date=now - timedelta(hours=2),
            received_date=now
        )

        assert sample.id is not None
        assert sample.tenant_id == TEST_TENANT_ID
        assert sample.external_lis_id == "LIS-SAMPLE-001"
        assert sample.patient_id == "PAT001"
        assert sample.specimen_type == "blood"
        assert sample.status == SampleStatus.PENDING

    def test_create_sample_with_invalid_dates(self, sample_service):
        """Test that collection_date cannot be after received_date."""
        now = datetime.utcnow()

        with pytest.raises(InvalidSampleDataError):
            sample_service.create_sample(
                tenant_id=TEST_TENANT_ID,
                external_lis_id="LIS-SAMPLE-002",
                patient_id="PAT002",
                specimen_type="urine",
                collection_date=now,  # Later than received_date
                received_date=now - timedelta(hours=1)
            )

    def test_create_duplicate_sample(self, sample_service):
        """Test that duplicate external_lis_id within tenant raises error."""
        now = datetime.utcnow()

        # Create first sample
        sample_service.create_sample(
            tenant_id=TEST_TENANT_ID,
            external_lis_id="LIS-SAMPLE-003",
            patient_id="PAT003",
            specimen_type="blood",
            collection_date=now - timedelta(hours=1),
            received_date=now
        )

        # Try to create duplicate
        with pytest.raises(DuplicateSampleError):
            sample_service.create_sample(
                tenant_id=TEST_TENANT_ID,
                external_lis_id="LIS-SAMPLE-003",  # Same ID
                patient_id="PAT004",
                specimen_type="serum",
                collection_date=now - timedelta(hours=1),
                received_date=now
            )

    def test_create_same_external_id_different_tenant(self, sample_service):
        """Test that same external_lis_id in different tenant is allowed."""
        now = datetime.utcnow()

        # Create sample in tenant 1
        sample1 = sample_service.create_sample(
            tenant_id=TEST_TENANT_ID,
            external_lis_id="LIS-SAMPLE-004",
            patient_id="PAT001",
            specimen_type="blood",
            collection_date=now - timedelta(hours=1),
            received_date=now
        )

        # Create sample with same external_lis_id in tenant 2 (should succeed)
        sample2 = sample_service.create_sample(
            tenant_id="tenant-2",
            external_lis_id="LIS-SAMPLE-004",  # Same ID
            patient_id="PAT005",
            specimen_type="serum",
            collection_date=now - timedelta(hours=1),
            received_date=now
        )

        assert sample1.id != sample2.id
        assert sample1.external_lis_id == sample2.external_lis_id


class TestSampleServiceGetSample:
    """Tests for retrieving samples."""

    def test_get_sample_success(self, sample_service):
        """Test successful sample retrieval."""
        now = datetime.utcnow()

        created = sample_service.create_sample(
            tenant_id=TEST_TENANT_ID,
            external_lis_id="LIS-SAMPLE-005",
            patient_id="PAT006",
            specimen_type="plasma",
            collection_date=now - timedelta(hours=2),
            received_date=now
        )

        retrieved = sample_service.get_sample(created.id, TEST_TENANT_ID)

        assert retrieved.id == created.id
        assert retrieved.external_lis_id == "LIS-SAMPLE-005"

    def test_get_sample_not_found(self, sample_service):
        """Test that getting non-existent sample raises error."""
        with pytest.raises(SampleNotFoundError):
            sample_service.get_sample("nonexistent-id", TEST_TENANT_ID)

    def test_get_sample_different_tenant(self, sample_service):
        """Test that sample cannot be accessed from different tenant."""
        now = datetime.utcnow()

        created = sample_service.create_sample(
            tenant_id=TEST_TENANT_ID,
            external_lis_id="LIS-SAMPLE-006",
            patient_id="PAT007",
            specimen_type="blood",
            collection_date=now - timedelta(hours=1),
            received_date=now
        )

        # Try to access with different tenant ID
        with pytest.raises(SampleNotFoundError):
            sample_service.get_sample(created.id, "different-tenant")

    def test_get_sample_by_external_id(self, sample_service):
        """Test retrieving sample by external LIS ID."""
        now = datetime.utcnow()

        created = sample_service.create_sample(
            tenant_id=TEST_TENANT_ID,
            external_lis_id="LIS-SAMPLE-007",
            patient_id="PAT008",
            specimen_type="urine",
            collection_date=now - timedelta(hours=1),
            received_date=now
        )

        retrieved = sample_service.get_sample_by_external_id("LIS-SAMPLE-007", TEST_TENANT_ID)

        assert retrieved is not None
        assert retrieved.id == created.id

    def test_get_sample_by_external_id_not_found(self, sample_service):
        """Test that non-existent external ID returns None."""
        result = sample_service.get_sample_by_external_id("nonexistent", TEST_TENANT_ID)
        assert result is None


class TestSampleServiceSearch:
    """Tests for searching samples."""

    def test_search_samples_all(self, sample_service):
        """Test retrieving all samples for a tenant."""
        now = datetime.utcnow()

        # Create multiple samples
        for i in range(3):
            sample_service.create_sample(
                tenant_id=TEST_TENANT_ID,
                external_lis_id=f"LIS-SAMPLE-{100+i}",
                patient_id=f"PAT{i}",
                specimen_type="blood",
                collection_date=now - timedelta(hours=i),
                received_date=now
            )

        samples, total = sample_service.search_samples(TEST_TENANT_ID)

        assert total == 3
        assert len(samples) == 3

    def test_search_samples_with_patient_filter(self, sample_service):
        """Test searching samples by patient ID."""
        now = datetime.utcnow()

        sample_service.create_sample(
            tenant_id=TEST_TENANT_ID,
            external_lis_id="LIS-SAMPLE-010",
            patient_id="PAT-ABC-123",
            specimen_type="blood",
            collection_date=now - timedelta(hours=1),
            received_date=now
        )

        sample_service.create_sample(
            tenant_id=TEST_TENANT_ID,
            external_lis_id="LIS-SAMPLE-011",
            patient_id="PAT-XYZ-456",
            specimen_type="urine",
            collection_date=now - timedelta(hours=1),
            received_date=now
        )

        # Search by patient ID (partial match)
        samples, total = sample_service.search_samples(
            tenant_id=TEST_TENANT_ID,
            patient_id="ABC"
        )

        assert total == 1
        assert samples[0].patient_id == "PAT-ABC-123"

    def test_search_samples_with_date_range(self, sample_service):
        """Test searching samples by date range."""
        now = datetime.utcnow()

        # Create samples on different dates
        sample_service.create_sample(
            tenant_id=TEST_TENANT_ID,
            external_lis_id="LIS-SAMPLE-020",
            patient_id="PAT001",
            specimen_type="blood",
            collection_date=now - timedelta(days=5),
            received_date=now - timedelta(days=5)
        )

        sample_service.create_sample(
            tenant_id=TEST_TENANT_ID,
            external_lis_id="LIS-SAMPLE-021",
            patient_id="PAT002",
            specimen_type="blood",
            collection_date=now - timedelta(days=2),
            received_date=now - timedelta(days=2)
        )

        # Search within date range
        samples, total = sample_service.search_samples(
            tenant_id=TEST_TENANT_ID,
            start_date=now - timedelta(days=3),
            end_date=now
        )

        assert total == 1
        assert samples[0].external_lis_id == "LIS-SAMPLE-021"

    def test_search_samples_with_specimen_type_filter(self, sample_service):
        """Test filtering samples by specimen type."""
        now = datetime.utcnow()

        sample_service.create_sample(
            tenant_id=TEST_TENANT_ID,
            external_lis_id="LIS-SAMPLE-030",
            patient_id="PAT001",
            specimen_type="blood",
            collection_date=now - timedelta(hours=1),
            received_date=now
        )

        sample_service.create_sample(
            tenant_id=TEST_TENANT_ID,
            external_lis_id="LIS-SAMPLE-031",
            patient_id="PAT002",
            specimen_type="urine",
            collection_date=now - timedelta(hours=1),
            received_date=now
        )

        samples, total = sample_service.search_samples(
            tenant_id=TEST_TENANT_ID,
            specimen_type="blood"
        )

        assert total == 1
        assert samples[0].specimen_type == "blood"

    def test_search_samples_pagination(self, sample_service):
        """Test pagination in sample search."""
        now = datetime.utcnow()

        # Create 5 samples
        for i in range(5):
            sample_service.create_sample(
                tenant_id=TEST_TENANT_ID,
                external_lis_id=f"LIS-SAMPLE-{200+i}",
                patient_id=f"PAT{i}",
                specimen_type="blood",
                collection_date=now - timedelta(hours=i),
                received_date=now
            )

        # Get first 2
        samples1, total = sample_service.search_samples(
            tenant_id=TEST_TENANT_ID,
            skip=0,
            limit=2
        )

        assert total == 5
        assert len(samples1) == 2

        # Get next 2
        samples2, _ = sample_service.search_samples(
            tenant_id=TEST_TENANT_ID,
            skip=2,
            limit=2
        )

        assert len(samples2) == 2
        assert samples1[0].id != samples2[0].id


class TestSampleServiceUpdate:
    """Tests for updating samples."""

    def test_update_sample_status(self, sample_service):
        """Test updating sample status."""
        now = datetime.utcnow()

        created = sample_service.create_sample(
            tenant_id=TEST_TENANT_ID,
            external_lis_id="LIS-SAMPLE-050",
            patient_id="PAT001",
            specimen_type="blood",
            collection_date=now - timedelta(hours=1),
            received_date=now
        )

        assert created.status == SampleStatus.PENDING

        updated = sample_service.update_sample_status(
            created.id,
            TEST_TENANT_ID,
            SampleStatus.VERIFIED
        )

        assert updated.status == SampleStatus.VERIFIED
        assert updated.updated_at > created.created_at
