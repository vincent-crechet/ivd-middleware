"""Shared tests for ResultDecision repository implementations.

Tests both in-memory and PostgreSQL adapters using parametrized fixtures.
"""

import pytest
import uuid
from app.models import ResultDecision
from app.ports import IResultDecisionRepository

TEST_TENANT_ID = "test-tenant-123"


class TestResultDecisionRepository:
    """Contract tests for IResultDecisionRepository."""

    def test_create_result_decision(self, result_decision_repository):
        """Test creating a new result decision."""
        repo = result_decision_repository
        review_id = str(uuid.uuid4())
        result_id = str(uuid.uuid4())

        decision = ResultDecision(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            review_id=review_id,
            result_id=result_id,
            decision="approved",
            comments=None,
        )

        created = repo.create(decision)

        assert created.id == decision.id
        assert created.tenant_id == TEST_TENANT_ID
        assert created.decision == "approved"

    def test_get_by_id(self, result_decision_repository):
        """Test retrieving result decision by ID."""
        repo = result_decision_repository
        review_id = str(uuid.uuid4())
        result_id = str(uuid.uuid4())

        decision = ResultDecision(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            review_id=review_id,
            result_id=result_id,
            decision="rejected",
            comments="Value out of range",
        )
        created = repo.create(decision)

        retrieved = repo.get_by_id(created.id, TEST_TENANT_ID)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.decision == "rejected"
        assert retrieved.comments == "Value out of range"

    def test_get_by_id_wrong_tenant(self, result_decision_repository):
        """Test that get_by_id enforces tenant isolation."""
        repo = result_decision_repository
        decision = ResultDecision(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            review_id=str(uuid.uuid4()),
            result_id=str(uuid.uuid4()),
            decision="approved",
            comments=None,
        )
        created = repo.create(decision)

        # Try to get with different tenant
        retrieved = repo.get_by_id(created.id, "other-tenant")

        assert retrieved is None

    def test_get_by_review(self, result_decision_repository):
        """Test retrieving all decisions for a review."""
        repo = result_decision_repository
        review_id = str(uuid.uuid4())

        # Create multiple decisions for same review
        decision1 = ResultDecision(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            review_id=review_id,
            result_id=str(uuid.uuid4()),
            decision="approved",
            comments=None,
        )
        decision2 = ResultDecision(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            review_id=review_id,
            result_id=str(uuid.uuid4()),
            decision="rejected",
            comments="High potassium",
        )

        repo.create(decision1)
        repo.create(decision2)

        # Get all decisions for this review
        decisions = repo.get_by_review(review_id, TEST_TENANT_ID)

        assert len(decisions) == 2
        statuses = {d.decision for d in decisions}
        assert statuses == {"approved", "rejected"}

    def test_get_by_review_empty(self, result_decision_repository):
        """Test getting decisions for review with no decisions."""
        repo = result_decision_repository

        decisions = repo.get_by_review(str(uuid.uuid4()), TEST_TENANT_ID)

        assert len(decisions) == 0

    def test_list_by_review_pagination(self, result_decision_repository):
        """Test paginated listing of decisions for a review."""
        repo = result_decision_repository
        review_id = str(uuid.uuid4())

        # Create 5 decisions
        for i in range(5):
            decision = ResultDecision(
                id=str(uuid.uuid4()),
                tenant_id=TEST_TENANT_ID,
                review_id=review_id,
                result_id=str(uuid.uuid4()),
                decision="approved" if i % 2 == 0 else "rejected",
                comments=None,
            )
            repo.create(decision)

        # Get first page (2 items)
        page1, count1 = repo.list_by_review(review_id, TEST_TENANT_ID, skip=0, limit=2)
        assert len(page1) == 2
        assert count1 == 5

        # Get second page
        page2, count2 = repo.list_by_review(review_id, TEST_TENANT_ID, skip=2, limit=2)
        assert len(page2) == 2
        assert count2 == 5

        # Get third page (1 item)
        page3, count3 = repo.list_by_review(review_id, TEST_TENANT_ID, skip=4, limit=2)
        assert len(page3) == 1
        assert count3 == 5

    def test_decisions_are_immutable(self, result_decision_repository):
        """Test that result decisions should not be updatable (immutable pattern)."""
        repo = result_decision_repository
        decision = ResultDecision(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            review_id=str(uuid.uuid4()),
            result_id=str(uuid.uuid4()),
            decision="approved",
            comments=None,
        )
        created = repo.create(decision)

        # Repository should not support update (immutable)
        # This test documents expected behavior
        assert hasattr(repo, "get_by_id")
        assert hasattr(repo, "create")
        assert not hasattr(repo, "update")

    def test_multiple_reviews_different_decisions(self, result_decision_repository):
        """Test that decisions from different reviews don't mix."""
        repo = result_decision_repository
        review1_id = str(uuid.uuid4())
        review2_id = str(uuid.uuid4())

        # Create decisions for review 1
        decision1_1 = ResultDecision(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            review_id=review1_id,
            result_id=str(uuid.uuid4()),
            decision="approved",
            comments=None,
        )
        decision1_2 = ResultDecision(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            review_id=review1_id,
            result_id=str(uuid.uuid4()),
            decision="approved",
            comments=None,
        )

        # Create decisions for review 2
        decision2_1 = ResultDecision(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            review_id=review2_id,
            result_id=str(uuid.uuid4()),
            decision="rejected",
            comments="Out of range",
        )

        repo.create(decision1_1)
        repo.create(decision1_2)
        repo.create(decision2_1)

        # Get decisions for review 1
        review1_decisions = repo.get_by_review(review1_id, TEST_TENANT_ID)
        assert len(review1_decisions) == 2
        assert all(d.review_id == review1_id for d in review1_decisions)

        # Get decisions for review 2
        review2_decisions = repo.get_by_review(review2_id, TEST_TENANT_ID)
        assert len(review2_decisions) == 1
        assert review2_decisions[0].review_id == review2_id

    def test_tenant_isolation(self, result_decision_repository):
        """Test that decisions are isolated per tenant."""
        repo = result_decision_repository
        tenant1 = "tenant-1"
        tenant2 = "tenant-2"
        review_id = str(uuid.uuid4())

        # Create decisions for different tenants
        decision1 = ResultDecision(
            id=str(uuid.uuid4()),
            tenant_id=tenant1,
            review_id=review_id,
            result_id=str(uuid.uuid4()),
            decision="approved",
            comments=None,
        )
        decision2 = ResultDecision(
            id=str(uuid.uuid4()),
            tenant_id=tenant2,
            review_id=review_id,
            result_id=str(uuid.uuid4()),
            decision="rejected",
            comments="Tenant 2 decision",
        )

        repo.create(decision1)
        repo.create(decision2)

        # Get for tenant1 should only return tenant1 decisions
        tenant1_decisions = repo.get_by_review(review_id, tenant1)
        assert len(tenant1_decisions) == 1
        assert tenant1_decisions[0].tenant_id == tenant1

        # Get for tenant2 should only return tenant2 decisions
        tenant2_decisions = repo.get_by_review(review_id, tenant2)
        assert len(tenant2_decisions) == 1
        assert tenant2_decisions[0].tenant_id == tenant2

    def test_decision_with_comments(self, result_decision_repository):
        """Test creating decision with detailed comments."""
        repo = result_decision_repository
        comments = "Patient has severe anemia. Recommend immediate physician notification."

        decision = ResultDecision(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            review_id=str(uuid.uuid4()),
            result_id=str(uuid.uuid4()),
            decision="rejected",
            comments=comments,
        )

        created = repo.create(decision)

        assert created.comments == comments

    def test_approved_vs_rejected_decisions(self, result_decision_repository):
        """Test handling of both approved and rejected decisions."""
        repo = result_decision_repository
        review_id = str(uuid.uuid4())

        # Create mixed decisions
        approved = ResultDecision(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            review_id=review_id,
            result_id=str(uuid.uuid4()),
            decision="approved",
            comments=None,
        )
        rejected = ResultDecision(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            review_id=review_id,
            result_id=str(uuid.uuid4()),
            decision="rejected",
            comments="Invalid",
        )

        repo.create(approved)
        repo.create(rejected)

        decisions = repo.get_by_review(review_id, TEST_TENANT_ID)

        assert len(decisions) == 2
        approved_count = sum(1 for d in decisions if d.decision == "approved")
        rejected_count = sum(1 for d in decisions if d.decision == "rejected")
        assert approved_count == 1
        assert rejected_count == 1
