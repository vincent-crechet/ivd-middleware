"""PostgreSQL implementation of result repository."""

from sqlmodel import Session, select
from typing import Optional
from datetime import datetime
import uuid

from app.ports import IResultRepository
from app.models import Result, ResultStatus, UploadStatus
from app.exceptions import DuplicateResultError, ResultNotFoundError, ResultImmutableError


class PostgresResultRepository(IResultRepository):
    """PostgreSQL implementation of result repository with multi-tenant support."""

    def __init__(self, session: Session):
        """
        Initialize with database session.

        Args:
            session: SQLModel database session
        """
        self._session = session

    def create(self, result: Result) -> Result:
        """Create a new result in PostgreSQL."""
        # Validate required fields
        if not result.tenant_id:
            raise ValueError("Result must have a tenant_id")
        if not result.sample_id:
            raise ValueError("Result must have a sample_id")

        # Check for duplicate external LIS result ID within tenant
        existing = self._session.exec(
            select(Result).where(
                Result.external_lis_result_id == result.external_lis_result_id,
                Result.tenant_id == result.tenant_id
            )
        ).first()

        if existing:
            raise DuplicateResultError(
                f"Result with external_lis_result_id '{result.external_lis_result_id}' already exists in tenant"
            )

        # Generate ID if not provided
        if not result.id:
            result.id = str(uuid.uuid4())

        self._session.add(result)
        self._session.commit()
        self._session.refresh(result)
        return result

    def get_by_id(self, result_id: str, tenant_id: str) -> Optional[Result]:
        """Retrieve result by ID, ensuring it belongs to tenant."""
        statement = select(Result).where(
            Result.id == result_id,
            Result.tenant_id == tenant_id
        )
        return self._session.exec(statement).first()

    def get_by_external_id(self, external_lis_result_id: str, tenant_id: str) -> Optional[Result]:
        """Retrieve result by external LIS ID within tenant."""
        statement = select(Result).where(
            Result.external_lis_result_id == external_lis_result_id,
            Result.tenant_id == tenant_id
        )
        return self._session.exec(statement).first()

    def list_by_sample(self, sample_id: str, tenant_id: str) -> list[Result]:
        """List all results for a specific sample."""
        statement = select(Result).where(
            Result.sample_id == sample_id,
            Result.tenant_id == tenant_id
        ).order_by(Result.created_at.desc())
        return list(self._session.exec(statement).all())

    def list_by_tenant(
        self,
        tenant_id: str,
        status: Optional[ResultStatus] = None,
        upload_status: Optional[UploadStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Result], int]:
        """List results for a tenant with optional filtering."""
        # Build base query
        query = select(Result).where(Result.tenant_id == tenant_id)

        # Apply filters
        if status:
            query = query.where(Result.verification_status == status)
        if upload_status:
            query = query.where(Result.upload_status == upload_status)

        # Get total count
        count_query = select(Result).where(Result.tenant_id == tenant_id)
        if status:
            count_query = count_query.where(Result.verification_status == status)
        if upload_status:
            count_query = count_query.where(Result.upload_status == upload_status)

        total = len(self._session.exec(count_query).all())

        # Sort and apply pagination
        query = query.order_by(Result.created_at.desc()).offset(skip).limit(limit)
        results = list(self._session.exec(query).all())

        return results, total

    def list_by_upload_status(
        self,
        tenant_id: str,
        upload_status: UploadStatus,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Result], int]:
        """List results by upload status for a tenant."""
        query = select(Result).where(
            Result.tenant_id == tenant_id,
            Result.upload_status == upload_status
        )

        total = len(self._session.exec(query).all())

        query = query.order_by(Result.created_at.asc()).offset(skip).limit(limit)
        results = list(self._session.exec(query).all())

        return results, total

    def list_for_upload(
        self,
        tenant_id: str,
        include_verified: bool = True,
        include_rejected: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Result], int]:
        """List results ready for upload to LIS."""
        # Build status filter
        statuses = []
        if include_verified:
            statuses.append(ResultStatus.VERIFIED)
        if include_rejected:
            statuses.append(ResultStatus.REJECTED)

        # Get results with pending upload status
        query = select(Result).where(
            Result.tenant_id == tenant_id,
            Result.upload_status == UploadStatus.PENDING,
            Result.verification_status.in_(statuses)
        )

        total = len(self._session.exec(query).all())

        query = query.order_by(Result.created_at.asc()).offset(skip).limit(limit)
        results = list(self._session.exec(query).all())

        return results, total

    def update(self, result: Result) -> Result:
        """Update existing result."""
        with self._session.no_autoflush:
            existing = self.get_by_id(result.id, result.tenant_id)
            if not existing:
                raise ResultNotFoundError(f"Result with id '{result.id}' not found")

            # Check immutability
            if existing.is_immutable():
                raise ResultImmutableError(
                    f"Result with id '{result.id}' is immutable (status: {existing.verification_status})"
                )

            # Update fields
            existing.test_code = result.test_code
            existing.test_name = result.test_name
            existing.value = result.value
            existing.unit = result.unit
            existing.reference_range_low = result.reference_range_low
            existing.reference_range_high = result.reference_range_high
            existing.lis_flags = result.lis_flags
            existing.update_timestamp()

        self._session.add(existing)
        self._session.commit()
        self._session.refresh(existing)
        return existing

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

        self._session.add(result)
        self._session.commit()
        self._session.refresh(result)
        return result

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

        self._session.add(result)
        self._session.commit()
        self._session.refresh(result)
        return result

    def delete(self, result_id: str, tenant_id: str) -> bool:
        """Delete a result, ensuring it belongs to the tenant."""
        result = self.get_by_id(result_id, tenant_id)
        if not result:
            return False

        self._session.delete(result)
        self._session.commit()
        return True
