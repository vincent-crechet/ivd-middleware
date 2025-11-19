"""PostgreSQL implementation of result decision repository."""

from sqlmodel import Session, select
from typing import Optional
import uuid

from app.ports import IResultDecisionRepository
from app.models import ResultDecision


class PostgresResultDecisionRepository(IResultDecisionRepository):
    """PostgreSQL implementation of result decision repository with multi-tenant support."""

    def __init__(self, session: Session):
        """
        Initialize with database session.

        Args:
            session: SQLModel database session
        """
        self._session = session

    def create(self, decision: ResultDecision) -> ResultDecision:
        """Create a new result decision in PostgreSQL."""
        # Validate required fields are set
        if not decision.tenant_id:
            raise ValueError("Decision must have a tenant_id")
        if not decision.review_id:
            raise ValueError("Decision must have a review_id")
        if not decision.result_id:
            raise ValueError("Decision must have a result_id")

        # Generate ID if not provided
        if not decision.id:
            decision.id = str(uuid.uuid4())

        self._session.add(decision)
        self._session.commit()
        self._session.refresh(decision)
        return decision

    def get_by_id(self, decision_id: str, tenant_id: str) -> Optional[ResultDecision]:
        """Retrieve a decision by ID, ensuring it belongs to the tenant."""
        statement = select(ResultDecision).where(
            ResultDecision.id == decision_id,
            ResultDecision.tenant_id == tenant_id
        )
        return self._session.exec(statement).first()

    def get_by_review(self, review_id: str, tenant_id: str) -> list[ResultDecision]:
        """List all decisions for a specific review."""
        statement = select(ResultDecision).where(
            ResultDecision.review_id == review_id,
            ResultDecision.tenant_id == tenant_id
        ).order_by(ResultDecision.decided_at)

        return list(self._session.exec(statement).all())

    def list_by_review(
        self,
        review_id: str,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[ResultDecision], int]:
        """List decisions for a review with pagination."""
        # Build base query
        query = select(ResultDecision).where(
            ResultDecision.review_id == review_id,
            ResultDecision.tenant_id == tenant_id
        )

        # Get total count
        count_query = select(ResultDecision).where(
            ResultDecision.review_id == review_id,
            ResultDecision.tenant_id == tenant_id
        )
        total = len(self._session.exec(count_query).all())

        # Apply sorting and pagination
        query = query.order_by(ResultDecision.decided_at).offset(skip).limit(limit)
        decisions = list(self._session.exec(query).all())

        return decisions, total
