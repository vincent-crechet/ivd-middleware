"""PostgreSQL implementation of review repository."""

from sqlmodel import Session, select
from typing import Optional
from datetime import datetime
import uuid

from app.ports import IReviewRepository
from app.models import Review, ReviewState
from app.exceptions import ReviewAlreadyExistsError, ReviewNotFoundError


class PostgresReviewRepository(IReviewRepository):
    """PostgreSQL implementation of review repository with multi-tenant support."""

    def __init__(self, session: Session):
        """
        Initialize with database session.

        Args:
            session: SQLModel database session
        """
        self._session = session

    def create(self, review: Review) -> Review:
        """Create a new review in PostgreSQL."""
        # Validate tenant_id and sample_id are set
        if not review.tenant_id:
            raise ValueError("Review must have a tenant_id")
        if not review.sample_id:
            raise ValueError("Review must have a sample_id")

        # Check for duplicate sample_id within tenant
        existing = self._session.exec(
            select(Review).where(
                Review.sample_id == review.sample_id,
                Review.tenant_id == review.tenant_id
            )
        ).first()

        if existing:
            raise ReviewAlreadyExistsError(
                f"Review for sample '{review.sample_id}' already exists in tenant"
            )

        # Generate ID if not provided
        if not review.id:
            review.id = str(uuid.uuid4())

        self._session.add(review)
        self._session.commit()
        self._session.refresh(review)
        return review

    def get_by_id(self, review_id: str, tenant_id: str) -> Optional[Review]:
        """Retrieve a review by ID, ensuring it belongs to the tenant."""
        statement = select(Review).where(
            Review.id == review_id,
            Review.tenant_id == tenant_id
        )
        return self._session.exec(statement).first()

    def get_by_sample_id(self, sample_id: str, tenant_id: str) -> Optional[Review]:
        """Retrieve a review by sample ID, ensuring it belongs to the tenant."""
        statement = select(Review).where(
            Review.sample_id == sample_id,
            Review.tenant_id == tenant_id
        )
        return self._session.exec(statement).first()

    def update(self, review: Review) -> Review:
        """Update an existing review."""
        with self._session.no_autoflush:
            existing = self.get_by_id(review.id, review.tenant_id)
            if not existing:
                raise ReviewNotFoundError(f"Review with id '{review.id}' not found")

            # Update fields
            existing.reviewer_user_id = review.reviewer_user_id
            existing.state = review.state
            existing.decision = review.decision
            existing.comments = review.comments
            existing.escalation_reason = review.escalation_reason
            existing.submitted_at = review.submitted_at
            existing.completed_at = review.completed_at
            existing.update_timestamp()

        self._session.add(existing)
        self._session.commit()
        self._session.refresh(existing)
        return existing

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
        # Build base query
        query = select(Review).where(Review.tenant_id == tenant_id)

        # Apply filters
        if state:
            query = query.where(Review.state == state)
        if reviewer_user_id:
            query = query.where(Review.reviewer_user_id == reviewer_user_id)
        if start_date:
            query = query.where(Review.created_at >= start_date)
        if end_date:
            query = query.where(Review.created_at <= end_date)

        # Get total count before pagination
        count_query = select(Review).where(Review.tenant_id == tenant_id)
        if state:
            count_query = count_query.where(Review.state == state)
        if reviewer_user_id:
            count_query = count_query.where(Review.reviewer_user_id == reviewer_user_id)
        if start_date:
            count_query = count_query.where(Review.created_at >= start_date)
        if end_date:
            count_query = count_query.where(Review.created_at <= end_date)

        total = len(self._session.exec(count_query).all())

        # Sort by created_at (newest first) and apply pagination
        query = query.order_by(Review.created_at.desc()).offset(skip).limit(limit)
        reviews = list(self._session.exec(query).all())

        return reviews, total

    def search(
        self,
        tenant_id: str,
        sample_id: Optional[str] = None,
        state: Optional[ReviewState] = None,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[Review], int]:
        """Search reviews with flexible filtering."""
        # Build base query
        query = select(Review).where(Review.tenant_id == tenant_id)

        # Apply filters
        if sample_id:
            query = query.where(Review.sample_id.ilike(f"%{sample_id}%"))
        if state:
            query = query.where(Review.state == state)

        # Get total count before pagination
        count_query = select(Review).where(Review.tenant_id == tenant_id)
        if sample_id:
            count_query = count_query.where(Review.sample_id.ilike(f"%{sample_id}%"))
        if state:
            count_query = count_query.where(Review.state == state)

        total = len(self._session.exec(count_query).all())

        # Sort by created_at (newest first) and apply pagination
        query = query.order_by(Review.created_at.desc()).offset(skip).limit(limit)
        reviews = list(self._session.exec(query).all())

        return reviews, total
