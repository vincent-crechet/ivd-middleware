"""In-memory implementation of result decision repository for testing."""

from typing import Optional
import uuid
import copy

from app.ports import IResultDecisionRepository
from app.models import ResultDecision


class InMemoryResultDecisionRepository(IResultDecisionRepository):
    """In-memory implementation of result decision repository for testing."""

    def __init__(self):
        """Initialize with empty storage."""
        self._decisions: dict[str, ResultDecision] = {}
        # Index by review_id for fast lookups
        self._by_review: dict[str, list[str]] = {}

    def create(self, decision: ResultDecision) -> ResultDecision:
        """Create a new result decision in memory."""
        if not decision.tenant_id:
            raise ValueError("Decision must have a tenant_id")
        if not decision.review_id:
            raise ValueError("Decision must have a review_id")
        if not decision.result_id:
            raise ValueError("Decision must have a result_id")

        # Generate ID if not provided
        if not decision.id:
            decision.id = str(uuid.uuid4())

        # Store copy to avoid external mutations
        self._decisions[decision.id] = copy.deepcopy(decision)

        # Update review index
        if decision.review_id not in self._by_review:
            self._by_review[decision.review_id] = []
        self._by_review[decision.review_id].append(decision.id)

        return copy.deepcopy(self._decisions[decision.id])

    def get_by_id(self, decision_id: str, tenant_id: str) -> Optional[ResultDecision]:
        """Retrieve a decision by ID, ensuring it belongs to the tenant."""
        decision = self._decisions.get(decision_id)
        if decision and decision.tenant_id == tenant_id:
            return copy.deepcopy(decision)
        return None

    def get_by_review(self, review_id: str, tenant_id: str) -> list[ResultDecision]:
        """List all decisions for a specific review."""
        decision_ids = self._by_review.get(review_id, [])
        decisions = []
        for decision_id in decision_ids:
            decision = self._decisions.get(decision_id)
            if decision and decision.tenant_id == tenant_id:
                decisions.append(copy.deepcopy(decision))

        # Sort by decided_at (oldest first)
        decisions.sort(key=lambda d: d.decided_at)
        return decisions

    def list_by_review(
        self,
        review_id: str,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[ResultDecision], int]:
        """List decisions for a review with pagination."""
        decisions = self.get_by_review(review_id, tenant_id)

        total = len(decisions)
        paginated = decisions[skip:skip + limit]

        return paginated, total
