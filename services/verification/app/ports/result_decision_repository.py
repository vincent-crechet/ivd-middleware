"""Result decision repository port."""

import abc
from typing import Optional
from app.models import ResultDecision


class IResultDecisionRepository(abc.ABC):
    """
    Port: Abstract contract for result decision data persistence with multi-tenant support.

    All queries automatically filter by tenant_id to ensure data isolation.
    Result decisions are immutable records of individual result verification decisions within a review.
    """

    @abc.abstractmethod
    def create(self, decision: ResultDecision) -> ResultDecision:
        """
        Create a new result decision.

        Args:
            decision: Decision entity to create (must have tenant_id, review_id, and result_id set)

        Returns:
            Created decision with generated ID

        Raises:
            DuplicateDecisionError: If decision for same result_id in review already exists
            ValueError: If required fields are missing
        """
        pass

    @abc.abstractmethod
    def get_by_id(self, decision_id: str, tenant_id: str) -> Optional[ResultDecision]:
        """
        Retrieve a decision by ID, ensuring it belongs to the tenant.

        Args:
            decision_id: Unique decision identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            Decision if found and belongs to tenant, None otherwise
        """
        pass

    @abc.abstractmethod
    def get_by_review(self, review_id: str, tenant_id: str) -> list[ResultDecision]:
        """
        List all decisions for a specific review.

        Args:
            review_id: Review identifier
            tenant_id: Tenant identifier for isolation

        Returns:
            List of all decisions for the review
        """
        pass

    @abc.abstractmethod
    def list_by_review(
        self,
        review_id: str,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[ResultDecision], int]:
        """
        List decisions for a review with pagination.

        Args:
            review_id: Review identifier
            tenant_id: Tenant identifier for isolation
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of decisions, total count)
        """
        pass
