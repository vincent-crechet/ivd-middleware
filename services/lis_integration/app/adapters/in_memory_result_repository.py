"""In-memory implementation of result repository for testing."""

from typing import Optional
from datetime import datetime
import uuid
import copy

from app.ports import IResultRepository
from app.models import Result, ResultStatus, UploadStatus
from app.exceptions import DuplicateResultError, ResultNotFoundError, ResultImmutableError


class InMemoryResultRepository(IResultRepository):
    """In-memory implementation of result repository for testing."""

    def __init__(self):
        """Initialize with empty storage."""
        self._results: dict[str, Result] = {}

    def create(self, result: Result) -> Result:
        """Create a new result in memory."""
        if not result.tenant_id:
            raise ValueError("Result must have a tenant_id")
        if not result.sample_id:
            raise ValueError("Result must have a sample_id")

        # Check for duplicate
        for existing in self._results.values():
            if (existing.external_lis_result_id == result.external_lis_result_id and
                existing.tenant_id == result.tenant_id):
                raise DuplicateResultError(
                    f"Result with external_lis_result_id '{result.external_lis_result_id}' already exists in tenant"
                )

        if not result.id:
            result.id = str(uuid.uuid4())

        self._results[result.id] = copy.deepcopy(result)
        return copy.deepcopy(self._results[result.id])

    def get_by_id(self, result_id: str, tenant_id: str) -> Optional[Result]:
        """Retrieve result by ID, ensuring it belongs to tenant."""
        result = self._results.get(result_id)
        if result and result.tenant_id == tenant_id:
            return copy.deepcopy(result)
        return None

    def get_by_external_id(self, external_lis_result_id: str, tenant_id: str) -> Optional[Result]:
        """Retrieve result by external LIS ID within tenant."""
        for result in self._results.values():
            if result.external_lis_result_id == external_lis_result_id and result.tenant_id == tenant_id:
                return copy.deepcopy(result)
        return None

    def list_by_sample(self, sample_id: str, tenant_id: str) -> list[Result]:
        """List all results for a specific sample."""
        results = [r for r in self._results.values()
                   if r.sample_id == sample_id and r.tenant_id == tenant_id]
        results.sort(key=lambda r: r.created_at, reverse=True)
        return [copy.deepcopy(r) for r in results]

    def list_by_tenant(
        self,
        tenant_id: str,
        status: Optional[ResultStatus] = None,
        upload_status: Optional[UploadStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Result], int]:
        """List results for a tenant with optional filtering."""
        results = [r for r in self._results.values() if r.tenant_id == tenant_id]

        if status:
            results = [r for r in results if r.verification_status == status]
        if upload_status:
            results = [r for r in results if r.upload_status == upload_status]

        results.sort(key=lambda r: r.created_at, reverse=True)
        total = len(results)
        paginated = results[skip:skip + limit]

        return [copy.deepcopy(r) for r in paginated], total

    def list_by_upload_status(
        self,
        tenant_id: str,
        upload_status: UploadStatus,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Result], int]:
        """List results by upload status for a tenant."""
        results = [r for r in self._results.values()
                   if r.tenant_id == tenant_id and r.upload_status == upload_status]
        results.sort(key=lambda r: r.created_at)

        total = len(results)
        paginated = results[skip:skip + limit]

        return [copy.deepcopy(r) for r in paginated], total

    def list_for_upload(
        self,
        tenant_id: str,
        include_verified: bool = True,
        include_rejected: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Result], int]:
        """List results ready for upload to LIS."""
        statuses = []
        if include_verified:
            statuses.append(ResultStatus.VERIFIED)
        if include_rejected:
            statuses.append(ResultStatus.REJECTED)

        results = [r for r in self._results.values()
                   if r.tenant_id == tenant_id and
                   r.upload_status == UploadStatus.PENDING and
                   r.verification_status in statuses]
        results.sort(key=lambda r: r.created_at)

        total = len(results)
        paginated = results[skip:skip + limit]

        return [copy.deepcopy(r) for r in paginated], total

    def update(self, result: Result) -> Result:
        """Update existing result."""
        if result.id not in self._results:
            raise ResultNotFoundError(f"Result with id '{result.id}' not found")

        existing = self._results[result.id]
        if existing.tenant_id != result.tenant_id:
            raise ResultNotFoundError(f"Result with id '{result.id}' not found")

        if existing.is_immutable():
            raise ResultImmutableError(
                f"Result with id '{result.id}' is immutable (status: {existing.verification_status})"
            )

        result.update_timestamp()
        self._results[result.id] = copy.deepcopy(result)
        return copy.deepcopy(result)

    def update_verification_status(
        self,
        result_id: str,
        tenant_id: str,
        status: ResultStatus,
        method: Optional[str] = None
    ) -> Result:
        """Update only the verification status of a result."""
        result = self.get_by_id(result_id, tenant_id)
        if not result:
            raise ResultNotFoundError(f"Result with id '{result_id}' not found")

        result.verification_status = status
        result.verification_method = method
        if status in (ResultStatus.VERIFIED, ResultStatus.REJECTED):
            result.verified_at = datetime.utcnow()
        result.update_timestamp()

        self._results[result_id] = copy.deepcopy(result)
        return copy.deepcopy(result)

    def update_upload_status(
        self,
        result_id: str,
        tenant_id: str,
        upload_status: UploadStatus,
        failure_reason: Optional[str] = None
    ) -> Result:
        """Update upload status tracking fields for a result."""
        result = self.get_by_id(result_id, tenant_id)
        if not result:
            raise ResultNotFoundError(f"Result with id '{result_id}' not found")

        result.upload_status = upload_status
        result.last_upload_attempt_at = datetime.utcnow()

        if upload_status == UploadStatus.SENT:
            result.sent_to_lis_at = datetime.utcnow()
            result.upload_failure_count = 0
            result.upload_failure_reason = None
        elif upload_status == UploadStatus.FAILED:
            result.upload_failure_count += 1
            result.upload_failure_reason = failure_reason

        result.update_timestamp()
        self._results[result_id] = copy.deepcopy(result)
        return copy.deepcopy(result)

    def delete(self, result_id: str, tenant_id: str) -> bool:
        """Delete a result, ensuring it belongs to the tenant."""
        result = self._results.get(result_id)
        if result and result.tenant_id == tenant_id:
            del self._results[result_id]
            return True
        return False
