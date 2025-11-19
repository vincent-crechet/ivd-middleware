"""In-memory implementation of review repository for testing."""

from typing import Optional
from datetime import datetime
import uuid
import copy

from app.ports import IReviewRepository
from app.models import Review, ReviewState
from app.exceptions import ReviewAlreadyExistsError, ReviewNotFoundError


class InMemoryReviewRepository(IReviewRepository):
    """In-memory implementation of review repository for testing."""

    def __init__(self):
        """Initialize with empty storage."""
        self._reviews: dict[str, Review] = {}

    def create(self, review: Review) -> Review:
        """Create a new review in memory."""
        if not review.tenant_id:
            raise ValueError("Review must have a tenant_id")
        if not review.sample_id:
            raise ValueError("Review must have a sample_id")

        # Check for duplicate sample_id within tenant
        for existing in self._reviews.values():
            if (existing.sample_id == review.sample_id and
                existing.tenant_id == review.tenant_id):
                raise ReviewAlreadyExistsError(
                    f"Review for sample '{review.sample_id}' already exists in tenant"
                )

        # Generate ID if not provided
        if not review.id:
            review.id = str(uuid.uuid4())

        # Store copy to avoid external mutations
        self._reviews[review.id] = copy.deepcopy(review)
        return copy.deepcopy(self._reviews[review.id])

    def get_by_id(self, review_id: str, tenant_id: str) -> Optional[Review]:
        """Retrieve a review by ID, ensuring it belongs to the tenant."""
        review = self._reviews.get(review_id)
        if review and review.tenant_id == tenant_id:
            return copy.deepcopy(review)
        return None

    def get_by_sample_id(self, sample_id: str, tenant_id: str) -> Optional[Review]:
        """Retrieve a review by sample ID, ensuring it belongs to the tenant."""
        for review in self._reviews.values():
            if review.sample_id == sample_id and review.tenant_id == tenant_id:
                return copy.deepcopy(review)
        return None

    def update(self, review: Review) -> Review:
        """Update an existing review."""
        if not review.id or review.id not in self._reviews:
            raise ReviewNotFoundError(f"Review with id '{review.id}' not found")

        existing = self._reviews[review.id]
        if existing.tenant_id != review.tenant_id:
            raise ReviewNotFoundError(f"Review with id '{review.id}' not found")

        review.update_timestamp()
        self._reviews[review.id] = copy.deepcopy(review)
        return copy.deepcopy(review)

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
        """List reviews for a tenant with optional filtering."""
        # Filter by tenant
        reviews = [r for r in self._reviews.values() if r.tenant_id == tenant_id]

        # Apply filters
        if state:
            reviews = [r for r in reviews if r.state == state]
        if reviewer_user_id:
            reviews = [r for r in reviews if r.reviewer_user_id == reviewer_user_id]
        if start_date:
            reviews = [r for r in reviews if r.created_at >= start_date]
        if end_date:
            reviews = [r for r in reviews if r.created_at <= end_date]

        # Sort by created_at (newest first)
        reviews.sort(key=lambda r: r.created_at, reverse=True)

        total = len(reviews)
        paginated = reviews[skip:skip + limit]

        return [copy.deepcopy(r) for r in paginated], total

    def search(
        self,
        tenant_id: str,
        sample_id: Optional[str] = None,
        state: Optional[ReviewState] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Review], int]:
        """Search reviews with flexible filtering."""
        # Filter by tenant
        reviews = [r for r in self._reviews.values() if r.tenant_id == tenant_id]

        # Apply filters
        if sample_id:
            reviews = [r for r in reviews if sample_id.lower() in r.sample_id.lower()]
        if state:
            reviews = [r for r in reviews if r.state == state]

        # Sort by created_at (newest first)
        reviews.sort(key=lambda r: r.created_at, reverse=True)

        total = len(reviews)
        paginated = reviews[skip:skip + limit]

        return [copy.deepcopy(r) for r in paginated], total
