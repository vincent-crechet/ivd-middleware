"""Review service implementation."""

import logging
from typing import Optional
from datetime import datetime

from app.ports.review_repository import IReviewRepository
from app.ports.result_decision_repository import IResultDecisionRepository
from app.models import (
    Review,
    ReviewState,
    ReviewDecision as ReviewDecisionType,
    ResultDecision,
)
from app.exceptions import (
    ReviewNotFoundError,
    ReviewAlreadyExistsError,
    ReviewCannotBeModifiedError,
    ReviewStateTransitionError,
    ResultNotFoundError,
    SampleNotFoundError,
    InvalidReviewDecisionError,
)

# Import from LIS integration service for result and sample management
# In production, this would be done via service-to-service communication
try:
    from services.lis_integration.app.ports.result_repository import IResultRepository
    from services.lis_integration.app.ports.sample_repository import ISampleRepository
    from services.lis_integration.app.models import ResultStatus, SampleStatus
except ImportError:
    # Fallback for when running in isolation
    from typing import Protocol
    from enum import Enum

    class ResultStatus(str, Enum):
        """Result verification status."""

        PENDING = "pending"
        VERIFIED = "verified"
        NEEDS_REVIEW = "needs_review"
        REJECTED = "rejected"

    class SampleStatus(str, Enum):
        """Sample status."""

        PENDING = "pending"
        VERIFIED = "verified"
        NEEDS_REVIEW = "needs_review"
        REJECTED = "rejected"

    class IResultRepository(Protocol):
        """Protocol for result repository."""

        def get_by_id(self, result_id: str, tenant_id: str):
            """Get result by ID."""
            ...

        def list_by_sample(self, sample_id: str, tenant_id: str):
            """List results by sample."""
            ...

        def update_verification_status(
            self, result_id: str, tenant_id: str, status, method: Optional[str] = None
        ):
            """Update verification status."""
            ...

    class ISampleRepository(Protocol):
        """Protocol for sample repository."""

        def get_by_id(self, sample_id: str, tenant_id: str):
            """Get sample by ID."""
            ...

        def update(self, sample):
            """Update sample."""
            ...


logger = logging.getLogger(__name__)


class ReviewService:
    """
    Service for manual review of test results that failed auto-verification.

    This service manages the review workflow including:
    1. Creating reviews for samples needing manual verification
    2. Assigning reviews to reviewers
    3. Processing approval/rejection decisions
    4. Escalating reviews to pathologists
    5. Maintaining immutable audit trails
    6. Updating result and sample statuses

    Attributes:
        review_repository: Repository for review records
        result_decision_repository: Repository for result decisions
        result_repository: Repository for test results
        sample_repository: Repository for samples
    """

    def __init__(
        self,
        review_repository: IReviewRepository,
        result_decision_repository: IResultDecisionRepository,
        result_repository: IResultRepository,
        sample_repository: ISampleRepository,
    ):
        """
        Initialize the review service.

        Args:
            review_repository: Repository for accessing reviews
            result_decision_repository: Repository for result decisions
            result_repository: Repository for accessing and updating results
            sample_repository: Repository for accessing and updating samples
        """
        self.review_repository = review_repository
        self.result_decision_repository = result_decision_repository
        self.result_repository = result_repository
        self.sample_repository = sample_repository

    def create_review(
        self,
        tenant_id: str,
        sample_id: str,
        reviewer_user_id: Optional[str] = None,
    ) -> Review:
        """
        Create a new review for a sample.

        Args:
            tenant_id: Tenant identifier
            sample_id: Sample identifier requiring review
            reviewer_user_id: Optional user ID to assign review to

        Returns:
            Created review record

        Raises:
            SampleNotFoundError: If sample doesn't exist
            ReviewAlreadyExistsError: If review already exists for this sample
        """
        logger.info(f"Creating review for sample {sample_id} in tenant {tenant_id}")

        # Verify sample exists
        sample = self.sample_repository.get_by_id(sample_id, tenant_id)
        if sample is None:
            raise SampleNotFoundError(
                f"Sample {sample_id} not found in tenant {tenant_id}"
            )

        # Check if review already exists
        existing_review = self.review_repository.get_by_sample_id(sample_id, tenant_id)
        if existing_review is not None:
            raise ReviewAlreadyExistsError(
                f"Review already exists for sample {sample_id}"
            )

        # Determine initial state
        if reviewer_user_id:
            state = ReviewState.IN_PROGRESS
        else:
            state = ReviewState.PENDING

        # Create review
        review = Review(
            tenant_id=tenant_id,
            sample_id=sample_id,
            reviewer_user_id=reviewer_user_id,
            state=state,
        )

        created_review = self.review_repository.create(review)
        logger.info(f"Created review {created_review.id} for sample {sample_id}")

        return created_review

    def get_review(self, review_id: str, tenant_id: str) -> dict:
        """
        Get review details including all result decisions.

        Args:
            review_id: Review identifier
            tenant_id: Tenant identifier

        Returns:
            Dictionary containing review details and result decisions

        Raises:
            ReviewNotFoundError: If review doesn't exist
        """
        logger.debug(f"Getting review {review_id} for tenant {tenant_id}")

        review = self.review_repository.get_by_id(review_id, tenant_id)
        if review is None:
            raise ReviewNotFoundError(
                f"Review {review_id} not found in tenant {tenant_id}"
            )

        # Load result decisions
        decisions = self.result_decision_repository.get_by_review(review_id, tenant_id)

        return {
            "review_id": review.id,
            "sample_id": review.sample_id,
            "reviewer_user_id": review.reviewer_user_id,
            "state": review.state.value,
            "decision": review.decision.value if review.decision else None,
            "comments": review.comments,
            "escalation_reason": review.escalation_reason,
            "created_at": review.created_at.isoformat(),
            "submitted_at": review.submitted_at.isoformat() if review.submitted_at else None,
            "completed_at": review.completed_at.isoformat() if review.completed_at else None,
            "updated_at": review.updated_at.isoformat(),
            "result_decisions": [
                {
                    "decision_id": d.id,
                    "result_id": d.result_id,
                    "decision": d.decision,
                    "comments": d.comments,
                    "decided_at": d.decided_at.isoformat(),
                }
                for d in decisions
            ],
        }

    def list_review_queue(
        self,
        tenant_id: str,
        state: Optional[ReviewState] = None,
        reviewer_user_id: Optional[str] = None,
        escalated_only: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> dict:
        """
        Get queue of samples needing review with optional filtering.

        Args:
            tenant_id: Tenant identifier
            state: Optional filter by review state
            reviewer_user_id: Optional filter by assigned reviewer
            escalated_only: If True, only return escalated reviews
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Dictionary containing list of reviews and total count
        """
        logger.debug(f"Listing review queue for tenant {tenant_id}")

        # Apply escalated filter if requested
        if escalated_only:
            state = ReviewState.ESCALATED

        reviews, total = self.review_repository.list_by_tenant(
            tenant_id=tenant_id,
            state=state,
            reviewer_user_id=reviewer_user_id,
            skip=skip,
            limit=limit,
        )

        return {
            "reviews": [
                {
                    "review_id": r.id,
                    "sample_id": r.sample_id,
                    "reviewer_user_id": r.reviewer_user_id,
                    "state": r.state.value,
                    "decision": r.decision.value if r.decision else None,
                    "created_at": r.created_at.isoformat(),
                    "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
                }
                for r in reviews
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    def approve_sample(
        self,
        review_id: str,
        tenant_id: str,
        user_id: str,
        comments: Optional[str] = None,
    ) -> Review:
        """
        Approve all results in a sample.

        Creates approval decisions for all results that need review in the sample.

        Args:
            review_id: Review identifier
            tenant_id: Tenant identifier
            user_id: User ID performing the approval
            comments: Optional approval comments

        Returns:
            Updated review record

        Raises:
            ReviewNotFoundError: If review doesn't exist
            ReviewCannotBeModifiedError: If review is already completed
            ReviewStateTransitionError: If state transition is invalid
        """
        logger.info(f"Approving all results in review {review_id} by user {user_id}")

        # Load review
        review = self._load_and_validate_review(review_id, tenant_id)

        # Validate state transition
        self._validate_state_transition(review, ReviewState.APPROVED)

        # Get all results for the sample that need review
        results = self.result_repository.list_by_sample(review.sample_id, tenant_id)
        results_needing_review = [
            r for r in results if r.verification_status == ResultStatus.NEEDS_REVIEW
        ]

        if not results_needing_review:
            logger.warning(
                f"No results needing review found for sample {review.sample_id}"
            )

        # Create approval decision for each result
        for result in results_needing_review:
            self._approve_result_internal(
                review_id=review_id,
                result_id=result.id,
                tenant_id=tenant_id,
                user_id=user_id,
                comments=comments,
            )

        # Update review status
        review.state = ReviewState.APPROVED
        review.decision = ReviewDecisionType.APPROVE_ALL
        review.comments = comments
        review.completed_at = datetime.utcnow()
        review.submitted_at = datetime.utcnow()
        review.update_timestamp()

        updated_review = self.review_repository.update(review)

        # Update sample status
        self._update_sample_status(review.sample_id, tenant_id, SampleStatus.VERIFIED)

        logger.info(f"Approved all results in review {review_id}")

        return updated_review

    def reject_sample(
        self,
        review_id: str,
        tenant_id: str,
        user_id: str,
        comments: Optional[str] = None,
    ) -> Review:
        """
        Reject entire sample and all its results.

        Creates rejection decisions for all results that need review in the sample.

        Args:
            review_id: Review identifier
            tenant_id: Tenant identifier
            user_id: User ID performing the rejection
            comments: Optional rejection reason

        Returns:
            Updated review record

        Raises:
            ReviewNotFoundError: If review doesn't exist
            ReviewCannotBeModifiedError: If review is already completed
            ReviewStateTransitionError: If state transition is invalid
        """
        logger.info(f"Rejecting all results in review {review_id} by user {user_id}")

        # Load review
        review = self._load_and_validate_review(review_id, tenant_id)

        # Validate state transition
        self._validate_state_transition(review, ReviewState.REJECTED)

        # Get all results for the sample that need review
        results = self.result_repository.list_by_sample(review.sample_id, tenant_id)
        results_needing_review = [
            r for r in results if r.verification_status == ResultStatus.NEEDS_REVIEW
        ]

        # Create rejection decision for each result
        for result in results_needing_review:
            self._reject_result_internal(
                review_id=review_id,
                result_id=result.id,
                tenant_id=tenant_id,
                user_id=user_id,
                comments=comments,
            )

        # Update review status
        review.state = ReviewState.REJECTED
        review.decision = ReviewDecisionType.REJECT_ALL
        review.comments = comments
        review.completed_at = datetime.utcnow()
        review.submitted_at = datetime.utcnow()
        review.update_timestamp()

        updated_review = self.review_repository.update(review)

        # Update sample status
        self._update_sample_status(review.sample_id, tenant_id, SampleStatus.REJECTED)

        logger.info(f"Rejected all results in review {review_id}")

        return updated_review

    def approve_result(
        self,
        review_id: str,
        result_id: str,
        tenant_id: str,
        user_id: str,
        comments: Optional[str] = None,
    ) -> ResultDecision:
        """
        Approve an individual result within a review.

        Args:
            review_id: Review identifier
            result_id: Result identifier to approve
            tenant_id: Tenant identifier
            user_id: User ID performing the approval
            comments: Optional approval comments

        Returns:
            Created result decision record

        Raises:
            ReviewNotFoundError: If review doesn't exist
            ResultNotFoundError: If result doesn't exist
            ReviewCannotBeModifiedError: If review is completed
        """
        logger.info(f"Approving result {result_id} in review {review_id} by user {user_id}")

        # Load and validate review
        review = self._load_and_validate_review(review_id, tenant_id)

        # Verify result exists and belongs to this sample
        result = self.result_repository.get_by_id(result_id, tenant_id)
        if result is None:
            raise ResultNotFoundError(
                f"Result {result_id} not found in tenant {tenant_id}"
            )
        if result.sample_id != review.sample_id:
            raise InvalidReviewDecisionError(
                f"Result {result_id} does not belong to sample {review.sample_id}"
            )

        # Create approval decision
        decision = self._approve_result_internal(
            review_id=review_id,
            result_id=result_id,
            tenant_id=tenant_id,
            user_id=user_id,
            comments=comments,
        )

        # Check if all results have been decided
        self._check_and_complete_review(review, tenant_id)

        return decision

    def reject_result(
        self,
        review_id: str,
        result_id: str,
        tenant_id: str,
        user_id: str,
        comments: Optional[str] = None,
    ) -> ResultDecision:
        """
        Reject an individual result within a review.

        Args:
            review_id: Review identifier
            result_id: Result identifier to reject
            tenant_id: Tenant identifier
            user_id: User ID performing the rejection
            comments: Optional rejection reason

        Returns:
            Created result decision record

        Raises:
            ReviewNotFoundError: If review doesn't exist
            ResultNotFoundError: If result doesn't exist
            ReviewCannotBeModifiedError: If review is completed
        """
        logger.info(f"Rejecting result {result_id} in review {review_id} by user {user_id}")

        # Load and validate review
        review = self._load_and_validate_review(review_id, tenant_id)

        # Verify result exists and belongs to this sample
        result = self.result_repository.get_by_id(result_id, tenant_id)
        if result is None:
            raise ResultNotFoundError(
                f"Result {result_id} not found in tenant {tenant_id}"
            )
        if result.sample_id != review.sample_id:
            raise InvalidReviewDecisionError(
                f"Result {result_id} does not belong to sample {review.sample_id}"
            )

        # Create rejection decision
        decision = self._reject_result_internal(
            review_id=review_id,
            result_id=result_id,
            tenant_id=tenant_id,
            user_id=user_id,
            comments=comments,
        )

        # Check if all results have been decided
        self._check_and_complete_review(review, tenant_id)

        return decision

    def escalate_review(
        self,
        review_id: str,
        tenant_id: str,
        user_id: str,
        reason: str,
    ) -> Review:
        """
        Escalate a review to a pathologist for expert review.

        Args:
            review_id: Review identifier
            tenant_id: Tenant identifier
            user_id: User ID performing the escalation
            reason: Reason for escalation

        Returns:
            Updated review record

        Raises:
            ReviewNotFoundError: If review doesn't exist
            ReviewCannotBeModifiedError: If review is already completed
            ReviewStateTransitionError: If state transition is invalid
        """
        logger.info(f"Escalating review {review_id} by user {user_id}: {reason}")

        # Load review
        review = self._load_and_validate_review(review_id, tenant_id)

        # Validate state transition
        self._validate_state_transition(review, ReviewState.ESCALATED)

        # Update review
        review.state = ReviewState.ESCALATED
        review.escalation_reason = reason
        review.submitted_at = datetime.utcnow()
        review.update_timestamp()

        updated_review = self.review_repository.update(review)

        logger.info(f"Escalated review {review_id} to pathologist")

        return updated_review

    def _load_and_validate_review(self, review_id: str, tenant_id: str) -> Review:
        """Load review and validate it can be modified."""
        review = self.review_repository.get_by_id(review_id, tenant_id)
        if review is None:
            raise ReviewNotFoundError(
                f"Review {review_id} not found in tenant {tenant_id}"
            )

        # Check if review is already completed
        if review.state in (ReviewState.APPROVED, ReviewState.REJECTED):
            raise ReviewCannotBeModifiedError(
                f"Review {review_id} is already {review.state.value} and cannot be modified"
            )

        return review

    def _validate_state_transition(
        self, review: Review, new_state: ReviewState
    ) -> None:
        """Validate that state transition is allowed."""
        valid_transitions = {
            ReviewState.PENDING: [ReviewState.IN_PROGRESS, ReviewState.APPROVED, ReviewState.REJECTED, ReviewState.ESCALATED],
            ReviewState.IN_PROGRESS: [ReviewState.APPROVED, ReviewState.REJECTED, ReviewState.ESCALATED],
            ReviewState.ESCALATED: [ReviewState.APPROVED, ReviewState.REJECTED],
            ReviewState.APPROVED: [],  # Terminal state
            ReviewState.REJECTED: [],  # Terminal state
        }

        if new_state not in valid_transitions.get(review.state, []):
            raise ReviewStateTransitionError(
                f"Cannot transition review from {review.state.value} to {new_state.value}"
            )

    def _approve_result_internal(
        self,
        review_id: str,
        result_id: str,
        tenant_id: str,
        user_id: str,
        comments: Optional[str],
    ) -> ResultDecision:
        """Internal method to approve a result."""
        # Create decision record
        decision = ResultDecision(
            tenant_id=tenant_id,
            review_id=review_id,
            result_id=result_id,
            decision="approved",
            comments=comments,
        )
        created_decision = self.result_decision_repository.create(decision)

        # Update result verification status
        self.result_repository.update_verification_status(
            result_id=result_id,
            tenant_id=tenant_id,
            status=ResultStatus.VERIFIED,
            method="manual",
        )

        logger.debug(f"Approved result {result_id} in review {review_id}")

        return created_decision

    def _reject_result_internal(
        self,
        review_id: str,
        result_id: str,
        tenant_id: str,
        user_id: str,
        comments: Optional[str],
    ) -> ResultDecision:
        """Internal method to reject a result."""
        # Create decision record
        decision = ResultDecision(
            tenant_id=tenant_id,
            review_id=review_id,
            result_id=result_id,
            decision="rejected",
            comments=comments,
        )
        created_decision = self.result_decision_repository.create(decision)

        # Update result verification status
        self.result_repository.update_verification_status(
            result_id=result_id,
            tenant_id=tenant_id,
            status=ResultStatus.REJECTED,
            method="manual",
        )

        logger.debug(f"Rejected result {result_id} in review {review_id}")

        return created_decision

    def _check_and_complete_review(self, review: Review, tenant_id: str) -> None:
        """Check if all results have been decided and complete review if so."""
        # Get all results for sample
        results = self.result_repository.list_by_sample(review.sample_id, tenant_id)
        results_needing_review = [
            r for r in results if r.verification_status == ResultStatus.NEEDS_REVIEW
        ]

        # If no more results need review, mark review as complete
        if not results_needing_review:
            decisions = self.result_decision_repository.get_by_review(
                review.id, tenant_id
            )

            # Determine overall decision
            approved_count = sum(1 for d in decisions if d.decision == "approved")
            rejected_count = sum(1 for d in decisions if d.decision == "rejected")

            if rejected_count == 0:
                review.decision = ReviewDecisionType.APPROVE_ALL
                review.state = ReviewState.APPROVED
                sample_status = SampleStatus.VERIFIED
            elif approved_count == 0:
                review.decision = ReviewDecisionType.REJECT_ALL
                review.state = ReviewState.REJECTED
                sample_status = SampleStatus.REJECTED
            else:
                review.decision = ReviewDecisionType.PARTIAL
                review.state = ReviewState.APPROVED
                sample_status = SampleStatus.VERIFIED  # At least some results verified

            review.completed_at = datetime.utcnow()
            review.submitted_at = review.submitted_at or datetime.utcnow()
            review.update_timestamp()

            self.review_repository.update(review)
            self._update_sample_status(review.sample_id, tenant_id, sample_status)

            logger.info(f"Completed review {review.id} with decision {review.decision.value}")

    def _update_sample_status(
        self, sample_id: str, tenant_id: str, status: SampleStatus
    ) -> None:
        """Update sample status."""
        sample = self.sample_repository.get_by_id(sample_id, tenant_id)
        if sample:
            sample.status = status
            sample.update_timestamp()
            self.sample_repository.update(sample)
            logger.debug(f"Updated sample {sample_id} status to {status.value}")
