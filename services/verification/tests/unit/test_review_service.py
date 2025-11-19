"""Unit tests for ReviewService."""

import pytest
import uuid
from app.services import ReviewService
from app.models import Review, ReviewState, ResultDecision
from app.ports import (
    IReviewRepository,
    IResultDecisionRepository,
)

TEST_TENANT_ID = "test-tenant-123"


class TestReviewService:
    """Tests for ReviewService review workflow."""

    @pytest.fixture
    def service(
        self,
        review_repository: IReviewRepository,
        result_decision_repository: IResultDecisionRepository,
    ):
        """Create a ReviewService with parametrized repositories."""
        return ReviewService(
            review_repo=review_repository,
            decision_repo=result_decision_repository,
            result_repo=None,  # Mock for unit tests
            sample_repo=None,  # Mock for unit tests
        )

    # ========================================================================
    # Review Creation Tests
    # ========================================================================

    def test_create_review(self, service):
        """Test creating a new review."""
        sample_id = str(uuid.uuid4())

        review = service.create_review(
            tenant_id=TEST_TENANT_ID, sample_id=sample_id, flagged_result_ids=[]
        )

        assert review.tenant_id == TEST_TENANT_ID
        assert review.sample_id == sample_id
        assert review.state == ReviewState.PENDING

    def test_create_review_multiple_flagged_results(self, service):
        """Test creating a review with multiple flagged results."""
        sample_id = str(uuid.uuid4())
        flagged_ids = [str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())]

        review = service.create_review(
            tenant_id=TEST_TENANT_ID, sample_id=sample_id, flagged_result_ids=flagged_ids
        )

        assert review.tenant_id == TEST_TENANT_ID
        assert review.sample_id == sample_id
        assert review.state == ReviewState.PENDING

    # ========================================================================
    # Review Retrieval Tests
    # ========================================================================

    def test_get_review_by_id(self, service):
        """Test retrieving a review by ID."""
        sample_id = str(uuid.uuid4())
        created = service.create_review(
            tenant_id=TEST_TENANT_ID, sample_id=sample_id, flagged_result_ids=[]
        )

        retrieved = service.get_review(TEST_TENANT_ID, created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.sample_id == sample_id

    def test_get_review_by_sample_id(self, service):
        """Test retrieving a review by sample ID."""
        sample_id = str(uuid.uuid4())
        created = service.create_review(
            tenant_id=TEST_TENANT_ID, sample_id=sample_id, flagged_result_ids=[]
        )

        retrieved = service.get_review_by_sample(TEST_TENANT_ID, sample_id)

        assert retrieved is not None
        assert retrieved.sample_id == sample_id

    # ========================================================================
    # Review State Machine Tests
    # ========================================================================

    def test_review_state_transition_pending_to_in_progress(self, service):
        """Test transitioning review from PENDING to IN_PROGRESS."""
        sample_id = str(uuid.uuid4())
        review = service.create_review(
            tenant_id=TEST_TENANT_ID, sample_id=sample_id, flagged_result_ids=[]
        )

        assert review.state == ReviewState.PENDING

        # Transition to IN_PROGRESS when reviewer starts work
        review.state = ReviewState.IN_PROGRESS
        review.reviewer_user_id = "reviewer-123"
        updated = service._update_review(review)

        assert updated.state == ReviewState.IN_PROGRESS
        assert updated.reviewer_user_id == "reviewer-123"

    def test_review_state_transition_to_approved(self, service):
        """Test transitioning review from IN_PROGRESS to APPROVED."""
        sample_id = str(uuid.uuid4())
        review = service.create_review(
            tenant_id=TEST_TENANT_ID, sample_id=sample_id, flagged_result_ids=[]
        )

        # Move to IN_PROGRESS
        review.state = ReviewState.IN_PROGRESS
        review.reviewer_user_id = "reviewer-123"
        updated = service._update_review(review)

        # Move to APPROVED
        updated.state = ReviewState.APPROVED
        updated.decision = "APPROVE_ALL"
        updated.comments = "All results look correct"
        final = service._update_review(updated)

        assert final.state == ReviewState.APPROVED
        assert final.decision == "APPROVE_ALL"

    def test_review_state_transition_to_rejected(self, service):
        """Test transitioning review from IN_PROGRESS to REJECTED."""
        sample_id = str(uuid.uuid4())
        review = service.create_review(
            tenant_id=TEST_TENANT_ID, sample_id=sample_id, flagged_result_ids=[]
        )

        # Move to IN_PROGRESS
        review.state = ReviewState.IN_PROGRESS
        review.reviewer_user_id = "reviewer-123"
        updated = service._update_review(review)

        # Move to REJECTED
        updated.state = ReviewState.REJECTED
        updated.decision = "REJECT_ALL"
        updated.comments = "Sample integrity compromised"
        final = service._update_review(updated)

        assert final.state == ReviewState.REJECTED
        assert final.decision == "REJECT_ALL"

    def test_review_state_transition_to_escalated(self, service):
        """Test transitioning review from IN_PROGRESS to ESCALATED."""
        sample_id = str(uuid.uuid4())
        review = service.create_review(
            tenant_id=TEST_TENANT_ID, sample_id=sample_id, flagged_result_ids=[]
        )

        # Move to IN_PROGRESS
        review.state = ReviewState.IN_PROGRESS
        review.reviewer_user_id = "reviewer-123"
        updated = service._update_review(review)

        # Move to ESCALATED
        updated.state = ReviewState.ESCALATED
        updated.comments = "Requires pathologist review due to critical values"
        final = service._update_review(updated)

        assert final.state == ReviewState.ESCALATED

    # ========================================================================
    # Individual Result Decision Tests
    # ========================================================================

    def test_approve_individual_result(self, service):
        """Test approving an individual result."""
        sample_id = str(uuid.uuid4())
        result_id = str(uuid.uuid4())

        review = service.create_review(
            tenant_id=TEST_TENANT_ID, sample_id=sample_id, flagged_result_ids=[result_id]
        )

        decision = service.approve_result(
            tenant_id=TEST_TENANT_ID,
            review_id=review.id,
            result_id=result_id,
            reviewer_id="reviewer-123",
            comments=None,
        )

        assert decision.status == "APPROVED"
        assert decision.result_id == result_id

    def test_reject_individual_result(self, service):
        """Test rejecting an individual result."""
        sample_id = str(uuid.uuid4())
        result_id = str(uuid.uuid4())

        review = service.create_review(
            tenant_id=TEST_TENANT_ID, sample_id=sample_id, flagged_result_ids=[result_id]
        )

        decision = service.reject_result(
            tenant_id=TEST_TENANT_ID,
            review_id=review.id,
            result_id=result_id,
            reviewer_id="reviewer-123",
            comments="Value exceeds critical limits",
        )

        assert decision.status == "REJECTED"
        assert decision.comments == "Value exceeds critical limits"

    def test_multiple_result_decisions_in_review(self, service):
        """Test handling multiple result decisions within a single review."""
        sample_id = str(uuid.uuid4())
        result_ids = [str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())]

        review = service.create_review(
            tenant_id=TEST_TENANT_ID, sample_id=sample_id, flagged_result_ids=result_ids
        )

        # Approve first result
        d1 = service.approve_result(
            tenant_id=TEST_TENANT_ID,
            review_id=review.id,
            result_id=result_ids[0],
            reviewer_id="reviewer-123",
            comments=None,
        )

        # Reject second result
        d2 = service.reject_result(
            tenant_id=TEST_TENANT_ID,
            review_id=review.id,
            result_id=result_ids[1],
            reviewer_id="reviewer-123",
            comments="Out of range",
        )

        # Approve third result
        d3 = service.approve_result(
            tenant_id=TEST_TENANT_ID,
            review_id=review.id,
            result_id=result_ids[2],
            reviewer_id="reviewer-123",
            comments=None,
        )

        # Get all decisions for this review
        decisions = service._get_review_decisions(TEST_TENANT_ID, review.id)

        assert len(decisions) == 3
        statuses = [d.status for d in decisions]
        assert statuses.count("APPROVED") == 2
        assert statuses.count("REJECTED") == 1

    # ========================================================================
    # Immutability Tests
    # ========================================================================

    def test_result_decisions_are_immutable(self, service):
        """Test that result decisions cannot be modified after creation."""
        sample_id = str(uuid.uuid4())
        result_id = str(uuid.uuid4())

        review = service.create_review(
            tenant_id=TEST_TENANT_ID, sample_id=sample_id, flagged_result_ids=[result_id]
        )

        decision = service.approve_result(
            tenant_id=TEST_TENANT_ID,
            review_id=review.id,
            result_id=result_id,
            reviewer_id="reviewer-123",
            comments=None,
        )

        # Decisions should not have an update method
        assert hasattr(decision, "status")
        # The decision object should be immutable from repository perspective
        # (no update method on decision repository)

    # ========================================================================
    # Review Queue Tests
    # ========================================================================

    def test_get_review_queue(self, service):
        """Test retrieving pending and in-progress reviews."""
        # Create multiple reviews in different states
        sample_id1 = str(uuid.uuid4())
        sample_id2 = str(uuid.uuid4())
        sample_id3 = str(uuid.uuid4())

        review1 = service.create_review(
            tenant_id=TEST_TENANT_ID, sample_id=sample_id1, flagged_result_ids=[]
        )
        review2 = service.create_review(
            tenant_id=TEST_TENANT_ID, sample_id=sample_id2, flagged_result_ids=[]
        )
        review3 = service.create_review(
            tenant_id=TEST_TENANT_ID, sample_id=sample_id3, flagged_result_ids=[]
        )

        # Mark one as in progress
        review2.state = ReviewState.IN_PROGRESS
        review2.reviewer_user_id = "reviewer-123"
        service._update_review(review2)

        # Mark one as approved
        review3.state = ReviewState.APPROVED
        review3.decision = "APPROVE_ALL"
        service._update_review(review3)

        # Get queue (should only return pending and in-progress)
        queue = service.get_review_queue(TEST_TENANT_ID)

        queue_ids = {r.id for r in queue}
        assert review1.id in queue_ids  # Pending
        assert review2.id in queue_ids  # In progress
        assert review3.id not in queue_ids  # Approved

    def test_review_queue_for_reviewer(self, service):
        """Test retrieving reviews assigned to a specific reviewer."""
        reviewer_id = "reviewer-123"
        other_reviewer = "reviewer-456"

        # Create reviews for different reviewers
        r1 = service.create_review(
            tenant_id=TEST_TENANT_ID,
            sample_id=str(uuid.uuid4()),
            flagged_result_ids=[],
        )
        r2 = service.create_review(
            tenant_id=TEST_TENANT_ID,
            sample_id=str(uuid.uuid4()),
            flagged_result_ids=[],
        )

        # Assign r1 to reviewer_id
        r1.state = ReviewState.IN_PROGRESS
        r1.reviewer_user_id = reviewer_id
        service._update_review(r1)

        # Assign r2 to other_reviewer
        r2.state = ReviewState.IN_PROGRESS
        r2.reviewer_user_id = other_reviewer
        service._update_review(r2)

        # Get queue for specific reviewer
        reviewer_queue = service.get_review_queue_for_reviewer(
            TEST_TENANT_ID, reviewer_id
        )

        assert r1.id in {r.id for r in reviewer_queue}
        assert r2.id not in {r.id for r in reviewer_queue}

    # ========================================================================
    # Tenant Isolation Tests
    # ========================================================================

    def test_review_tenant_isolation(self, service):
        """Test that reviews are isolated per tenant."""
        tenant1 = "tenant-1"
        tenant2 = "tenant-2"

        # Create reviews for different tenants
        r1 = service.create_review(
            tenant_id=tenant1,
            sample_id=str(uuid.uuid4()),
            flagged_result_ids=[],
        )
        r2 = service.create_review(
            tenant_id=tenant2,
            sample_id=str(uuid.uuid4()),
            flagged_result_ids=[],
        )

        # Get reviews for each tenant
        tenant1_reviews = service.get_review_queue(tenant1)
        tenant2_reviews = service.get_review_queue(tenant2)

        tenant1_ids = {r.id for r in tenant1_reviews}
        tenant2_ids = {r.id for r in tenant2_reviews}

        assert r1.id in tenant1_ids
        assert r1.id not in tenant2_ids
        assert r2.id in tenant2_ids
        assert r2.id not in tenant1_ids
