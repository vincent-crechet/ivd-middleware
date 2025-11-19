"""Tests for ResultService (shared tests run against in-memory and PostgreSQL)."""

import pytest
from datetime import datetime, timedelta

from app.models import ResultStatus, UploadStatus
from app.exceptions import ResultNotFoundError, InvalidResultDataError, DuplicateResultError
from app.services import SampleService


TEST_TENANT_ID = "test-tenant-123"


@pytest.fixture
def sample_with_id(sample_service):
    """Create a sample for use in result tests."""
    now = datetime.utcnow()
    sample = sample_service.create_sample(
        tenant_id=TEST_TENANT_ID,
        external_lis_id="LIS-SAMPLE-TEST",
        patient_id="PAT-TEST",
        specimen_type="blood",
        collection_date=now - timedelta(hours=1),
        received_date=now
    )
    return sample


class TestResultServiceCreateResult:
    """Tests for creating results."""

    def test_create_result_success(self, result_service, sample_with_id):
        """Test successful result creation."""
        result = result_service.create_result(
            tenant_id=TEST_TENANT_ID,
            sample_id=sample_with_id.id,
            external_lis_result_id="LIS-RESULT-001",
            test_code="GLU",
            test_name="Glucose",
            value="95",
            unit="mg/dL",
            reference_range_low=70.0,
            reference_range_high=100.0
        )

        assert result.id is not None
        assert result.sample_id == sample_with_id.id
        assert result.test_code == "GLU"
        assert result.verification_status == ResultStatus.PENDING
        assert result.upload_status == UploadStatus.PENDING

    def test_create_result_with_invalid_reference_range(self, result_service, sample_with_id):
        """Test that invalid reference range raises error."""
        with pytest.raises(InvalidResultDataError):
            result_service.create_result(
                tenant_id=TEST_TENANT_ID,
                sample_id=sample_with_id.id,
                external_lis_result_id="LIS-RESULT-002",
                test_code="GLU",
                test_name="Glucose",
                value="95",
                unit="mg/dL",
                reference_range_low=100.0,  # High < low (invalid)
                reference_range_high=70.0
            )

    def test_create_duplicate_result(self, result_service, sample_with_id):
        """Test that duplicate external_lis_result_id raises error."""
        result_service.create_result(
            tenant_id=TEST_TENANT_ID,
            sample_id=sample_with_id.id,
            external_lis_result_id="LIS-RESULT-003",
            test_code="GLU",
            test_name="Glucose",
            value="95",
            unit="mg/dL"
        )

        # Try to create duplicate
        with pytest.raises(DuplicateResultError):
            result_service.create_result(
                tenant_id=TEST_TENANT_ID,
                sample_id=sample_with_id.id,
                external_lis_result_id="LIS-RESULT-003",  # Same ID
                test_code="WBC",
                test_name="White Blood Cell",
                value="7.2",
                unit="K/uL"
            )


class TestResultServiceGetResult:
    """Tests for retrieving results."""

    def test_get_result_success(self, result_service, sample_with_id):
        """Test successful result retrieval."""
        created = result_service.create_result(
            tenant_id=TEST_TENANT_ID,
            sample_id=sample_with_id.id,
            external_lis_result_id="LIS-RESULT-010",
            test_code="RBC",
            test_name="Red Blood Cell",
            value="4.8",
            unit="M/uL"
        )

        retrieved = result_service.get_result(created.id, TEST_TENANT_ID)

        assert retrieved.id == created.id
        assert retrieved.test_code == "RBC"

    def test_get_result_not_found(self, result_service):
        """Test that getting non-existent result raises error."""
        with pytest.raises(ResultNotFoundError):
            result_service.get_result("nonexistent-id", TEST_TENANT_ID)

    def test_get_result_by_external_id(self, result_service, sample_with_id):
        """Test retrieving result by external LIS ID."""
        created = result_service.create_result(
            tenant_id=TEST_TENANT_ID,
            sample_id=sample_with_id.id,
            external_lis_result_id="LIS-RESULT-011",
            test_code="HGB",
            test_name="Hemoglobin",
            value="14.5",
            unit="g/dL"
        )

        retrieved = result_service.get_result_by_external_id(
            "LIS-RESULT-011",
            TEST_TENANT_ID
        )

        assert retrieved is not None
        assert retrieved.id == created.id


class TestResultServiceListResults:
    """Tests for listing results."""

    def test_list_results_by_sample(self, result_service, sample_with_id):
        """Test listing all results for a sample."""
        # Create 3 results for the same sample
        for i in range(3):
            result_service.create_result(
                tenant_id=TEST_TENANT_ID,
                sample_id=sample_with_id.id,
                external_lis_result_id=f"LIS-RESULT-{100+i}",
                test_code=f"TEST{i}",
                test_name=f"Test {i}",
                value=str(i*10),
                unit="units"
            )

        results = result_service.list_results_by_sample(
            sample_with_id.id,
            TEST_TENANT_ID
        )

        assert len(results) == 3

    def test_search_results_by_status(self, result_service, sample_with_id):
        """Test searching results by verification status."""
        # Create results
        result1 = result_service.create_result(
            tenant_id=TEST_TENANT_ID,
            sample_id=sample_with_id.id,
            external_lis_result_id="LIS-RESULT-020",
            test_code="GLU",
            test_name="Glucose",
            value="95",
            unit="mg/dL"
        )

        result2 = result_service.create_result(
            tenant_id=TEST_TENANT_ID,
            sample_id=sample_with_id.id,
            external_lis_result_id="LIS-RESULT-021",
            test_code="WBC",
            test_name="White Blood Cell",
            value="7.2",
            unit="K/uL"
        )

        # Update result1 to verified
        result_service.update_verification_status(
            result1.id,
            TEST_TENANT_ID,
            ResultStatus.VERIFIED,
            "auto"
        )

        # Search verified
        verified, _ = result_service.search_results(
            TEST_TENANT_ID,
            status=ResultStatus.VERIFIED
        )

        assert len(verified) == 1
        assert verified[0].id == result1.id

        # Search pending
        pending, _ = result_service.search_results(
            TEST_TENANT_ID,
            status=ResultStatus.PENDING
        )

        assert len(pending) == 1
        assert pending[0].id == result2.id

    def test_list_results_for_upload(self, result_service, sample_with_id):
        """Test listing results ready for upload to LIS."""
        # Create results
        result1 = result_service.create_result(
            tenant_id=TEST_TENANT_ID,
            sample_id=sample_with_id.id,
            external_lis_result_id="LIS-RESULT-030",
            test_code="GLU",
            test_name="Glucose",
            value="95",
            unit="mg/dL"
        )

        # Verify result
        result_service.update_verification_status(
            result1.id,
            TEST_TENANT_ID,
            ResultStatus.VERIFIED
        )

        # List for upload
        results, total = result_service.list_results_for_upload(
            TEST_TENANT_ID,
            include_verified=True
        )

        assert total == 1
        assert results[0].id == result1.id
        assert results[0].upload_status == UploadStatus.PENDING


class TestResultServiceVerificationStatus:
    """Tests for updating verification status."""

    def test_update_verification_status_auto(self, result_service, sample_with_id):
        """Test auto-verification status update."""
        created = result_service.create_result(
            tenant_id=TEST_TENANT_ID,
            sample_id=sample_with_id.id,
            external_lis_result_id="LIS-RESULT-040",
            test_code="GLU",
            test_name="Glucose",
            value="95",
            unit="mg/dL"
        )

        updated = result_service.update_verification_status(
            created.id,
            TEST_TENANT_ID,
            ResultStatus.VERIFIED,
            method="auto"
        )

        assert updated.verification_status == ResultStatus.VERIFIED
        assert updated.verification_method == "auto"
        assert updated.verified_at is not None

    def test_update_verification_status_manual(self, result_service, sample_with_id):
        """Test manual review status update."""
        created = result_service.create_result(
            tenant_id=TEST_TENANT_ID,
            sample_id=sample_with_id.id,
            external_lis_result_id="LIS-RESULT-041",
            test_code="WBC",
            test_name="White Blood Cell",
            value="7.2",
            unit="K/uL"
        )

        updated = result_service.update_verification_status(
            created.id,
            TEST_TENANT_ID,
            ResultStatus.NEEDS_REVIEW,
            method="manual"
        )

        assert updated.verification_status == ResultStatus.NEEDS_REVIEW
        assert updated.verification_method == "manual"


class TestResultServiceUploadStatus:
    """Tests for upload status tracking."""

    def test_mark_result_sent(self, result_service, sample_with_id):
        """Test marking result as sent to LIS."""
        created = result_service.create_result(
            tenant_id=TEST_TENANT_ID,
            sample_id=sample_with_id.id,
            external_lis_result_id="LIS-RESULT-050",
            test_code="GLU",
            test_name="Glucose",
            value="95",
            unit="mg/dL"
        )

        updated = result_service.mark_result_sent(
            created.id,
            TEST_TENANT_ID
        )

        assert updated.upload_status == UploadStatus.SENT
        assert updated.sent_to_lis_at is not None
        assert updated.upload_failure_count == 0

    def test_mark_result_upload_failed(self, result_service, sample_with_id):
        """Test marking result upload as failed."""
        created = result_service.create_result(
            tenant_id=TEST_TENANT_ID,
            sample_id=sample_with_id.id,
            external_lis_result_id="LIS-RESULT-051",
            test_code="RBC",
            test_name="Red Blood Cell",
            value="4.8",
            unit="M/uL"
        )

        updated = result_service.mark_result_upload_failed(
            created.id,
            TEST_TENANT_ID,
            "Connection timeout"
        )

        assert updated.upload_status == UploadStatus.FAILED
        assert updated.upload_failure_count == 1
        assert updated.upload_failure_reason == "Connection timeout"

        # Mark failed again (should increment counter)
        updated2 = result_service.mark_result_upload_failed(
            created.id,
            TEST_TENANT_ID,
            "Connection timeout"
        )

        assert updated2.upload_failure_count == 2
