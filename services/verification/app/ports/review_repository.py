"""Review repository port."""

import abc
from typing import Optional
from datetime import datetime
from app.models import Review, ReviewState


class IReviewRepository(abc.ABC):
    """
    Port: Abstract contract for review data persistence with multi-tenant support.

    All queries automatically filter by tenant_id to ensure data isolation.
    Reviews track manual verification decisions for samples that failed auto-verification.
    """

    @abc.abstractmethod
    def create(self, review: Review) -> Review:
        """
        Create a new review.

        Args:
            review: Review entity to create (must have tenant_id and sample_id set)

        Returns:
            Created review with generated ID

        Raises:
            DuplicateReviewError: If review for same sample_id already exists
            ValueError: If required fields are missing
        """
        pass

    @abc.abstractmethod
    def get_by_id(self, review_id: str, tenant_id: str) -> Optional[Review]:
        """
        Retrieve a review by ID, ensuring it belongs to the tenant.

        Args:
            review_id: Unique review identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            Review if found and belongs to tenant, None otherwise
        """
        pass

    @abc.abstractmethod
    def get_by_sample_id(self, sample_id: str, tenant_id: str) -> Optional[Review]:
        """
        Retrieve a review by sample ID, ensuring it belongs to the tenant.

        Args:
            sample_id: Sample identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            Review if found for the sample in tenant, None otherwise
        """
        pass

    @abc.abstractmethod
    def update(self, review: Review) -> Review:
        """
        Update an existing review.

        Args:
            review: Review with updated fields (must have ID)

        Returns:
            Updated review

        Raises:
            ReviewNotFoundError: If review doesn't exist
            ReviewImmutableError: If trying to modify a completed review
        """
        pass

    @abc.abstractmethod
    def list_by_tenant(
        self,
        tenant_id: str,
        state: Optional[ReviewState] = None,
        reviewer_user_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Review], int]:
        """
        List reviews for a tenant with optional filtering.

        Args:
            tenant_id: Tenant identifier
            state: Optional review state filter
            reviewer_user_id: Optional filter by assigned reviewer
            start_date: Optional start of date range (based on created_at)
            end_date: Optional end of date range (based on created_at)
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of reviews, total count)
        """
        pass

    @abc.abstractmethod
    def search(
        self,
        tenant_id: str,
        sample_id: Optional[str] = None,
        state: Optional[ReviewState] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Review], int]:
        """
        Search reviews with flexible filtering.

        Args:
            tenant_id: Tenant identifier
            sample_id: Optional sample ID (partial match)
            state: Optional review state filter
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of reviews matching criteria, total count)
        """
        pass
