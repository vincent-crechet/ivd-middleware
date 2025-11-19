"""Shared tests for Review repository implementations.

Tests both in-memory and PostgreSQL adapters using parametrized fixtures.
"""

import pytest
import uuid
from datetime import datetime, timedelta
from app.models import Review, ReviewState
from app.ports import IReviewRepository

TEST_TENANT_ID = "test-tenant-123"


class TestReviewRepository:
    """Contract tests for IReviewRepository."""

    def test_create_review(self, review_repository):
        """Test creating a new review."""
        repo = review_repository
        review = Review(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            sample_id=str(uuid.uuid4()),
            reviewer_user_id=None,
            state=ReviewState.PENDING,
            decision=None,
            comments=None,
        )

        created = repo.create(review)

        assert created.id == review.id
        assert created.tenant_id == TEST_TENANT_ID
        assert created.state == ReviewState.PENDING

    def test_get_by_id(self, review_repository):
        """Test retrieving review by ID."""
        repo = review_repository
        review = Review(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            sample_id=str(uuid.uuid4()),
            reviewer_user_id=None,
            state=ReviewState.PENDING,
            decision=None,
            comments=None,
        )
        created = repo.create(review)

        retrieved = repo.get_by_id(created.id, TEST_TENANT_ID)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.sample_id == created.sample_id

    def test_get_by_id_wrong_tenant(self, review_repository):
        """Test that get_by_id enforces tenant isolation."""
        repo = review_repository
        review = Review(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            sample_id=str(uuid.uuid4()),
            reviewer_user_id=None,
            state=ReviewState.PENDING,
            decision=None,
            comments=None,
        )
        created = repo.create(review)

        # Try to get with different tenant
        retrieved = repo.get_by_id(created.id, "other-tenant")

        assert retrieved is None

    def test_get_by_sample_id(self, review_repository):
        """Test retrieving review by sample ID."""
        repo = review_repository
        sample_id = str(uuid.uuid4())
        review = Review(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            sample_id=sample_id,
            reviewer_user_id=None,
            state=ReviewState.PENDING,
            decision=None,
            comments=None,
        )
        repo.create(review)

        retrieved = repo.get_by_sample_id(sample_id, TEST_TENANT_ID)

        assert retrieved is not None
        assert retrieved.sample_id == sample_id

    def test_update_review_state(self, review_repository):
        """Test updating review state."""
        repo = review_repository
        review = Review(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            sample_id=str(uuid.uuid4()),
            reviewer_user_id=None,
            state=ReviewState.PENDING,
            decision=None,
            comments=None,
        )
        created = repo.create(review)

        # Update state
        created.state = ReviewState.IN_PROGRESS
        created.reviewer_user_id = "user-123"

        updated = repo.update(created)

        assert updated.state == ReviewState.IN_PROGRESS
        assert updated.reviewer_user_id == "user-123"

    def test_list_by_tenant_with_state_filter(self, review_repository):
        """Test listing reviews by state filter."""
        repo = review_repository

        # Create reviews in different states
        pending = Review(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            sample_id=str(uuid.uuid4()),
            reviewer_user_id=None,
            state=ReviewState.PENDING,
            decision=None,
            comments=None,
        )
        in_progress = Review(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            sample_id=str(uuid.uuid4()),
            reviewer_user_id="user-123",
            state=ReviewState.IN_PROGRESS,
            decision=None,
            comments=None,
        )
        approved = Review(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            sample_id=str(uuid.uuid4()),
            reviewer_user_id="user-123",
            state=ReviewState.APPROVED,
            decision="APPROVE_ALL",
            comments="Looks good",
        )

        repo.create(pending)
        repo.create(in_progress)
        repo.create(approved)

        # List pending reviews
        pending_reviews, count = repo.list_by_tenant(
            TEST_TENANT_ID, state=ReviewState.PENDING
        )
        assert len(pending_reviews) == 1
        assert pending_reviews[0].id == pending.id
        assert count == 1

        # List in-progress reviews
        in_progress_reviews, count = repo.list_by_tenant(
            TEST_TENANT_ID, state=ReviewState.IN_PROGRESS
        )
        assert len(in_progress_reviews) == 1
        assert in_progress_reviews[0].id == in_progress.id
        assert count == 1

    def test_list_by_tenant_with_reviewer_filter(self, review_repository):
        """Test listing reviews assigned to a reviewer."""
        repo = review_repository
        reviewer_id = "reviewer-123"

        # Create reviews for different reviewers
        review1 = Review(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            sample_id=str(uuid.uuid4()),
            reviewer_user_id=reviewer_id,
            state=ReviewState.IN_PROGRESS,
            decision=None,
            comments=None,
        )
        review2 = Review(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            sample_id=str(uuid.uuid4()),
            reviewer_user_id="other-reviewer",
            state=ReviewState.IN_PROGRESS,
            decision=None,
            comments=None,
        )

        repo.create(review1)
        repo.create(review2)

        # List reviews for specific reviewer
        reviewer_reviews, count = repo.list_by_tenant(
            TEST_TENANT_ID, reviewer_user_id=reviewer_id
        )

        assert len(reviewer_reviews) == 1
        assert reviewer_reviews[0].reviewer_user_id == reviewer_id
        assert count == 1

    def test_list_by_tenant_pagination(self, review_repository):
        """Test pagination when listing reviews."""
        repo = review_repository

        # Create multiple reviews
        for i in range(5):
            review = Review(
                id=str(uuid.uuid4()),
                tenant_id=TEST_TENANT_ID,
                sample_id=str(uuid.uuid4()),
                reviewer_user_id=None,
                state=ReviewState.PENDING,
                decision=None,
                comments=None,
            )
            repo.create(review)

        # Get first page (2 items per page)
        page1, count1 = repo.list_by_tenant(TEST_TENANT_ID, skip=0, limit=2)
        assert len(page1) == 2
        assert count1 == 5

        # Get second page
        page2, count2 = repo.list_by_tenant(TEST_TENANT_ID, skip=2, limit=2)
        assert len(page2) == 2
        assert count2 == 5

        # Get third page
        page3, count3 = repo.list_by_tenant(TEST_TENANT_ID, skip=4, limit=2)
        assert len(page3) == 1
        assert count3 == 5

    def test_search_reviews_by_sample_id(self, review_repository):
        """Test searching reviews by sample ID."""
        repo = review_repository
        sample_id = str(uuid.uuid4())

        review = Review(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            sample_id=sample_id,
            reviewer_user_id=None,
            state=ReviewState.PENDING,
            decision=None,
            comments=None,
        )
        repo.create(review)

        # Search by sample_id
        results, count = repo.search(TEST_TENANT_ID, sample_id=sample_id)

        assert len(results) == 1
        assert results[0].sample_id == sample_id
        assert count == 1

    def test_search_reviews_by_state(self, review_repository):
        """Test searching reviews by state."""
        repo = review_repository

        pending = Review(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            sample_id=str(uuid.uuid4()),
            reviewer_user_id=None,
            state=ReviewState.PENDING,
            decision=None,
            comments=None,
        )
        approved = Review(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            sample_id=str(uuid.uuid4()),
            reviewer_user_id="user-123",
            state=ReviewState.APPROVED,
            decision="APPROVE_ALL",
            comments="OK",
        )

        repo.create(pending)
        repo.create(approved)

        # Search for pending reviews
        results, count = repo.search(TEST_TENANT_ID, state=ReviewState.PENDING)

        assert len(results) == 1
        assert results[0].state == ReviewState.PENDING
        assert count == 1

    def test_search_reviews_pagination(self, review_repository):
        """Test pagination in search results."""
        repo = review_repository

        # Create 5 reviews
        for i in range(5):
            review = Review(
                id=str(uuid.uuid4()),
                tenant_id=TEST_TENANT_ID,
                sample_id=str(uuid.uuid4()),
                reviewer_user_id=None,
                state=ReviewState.PENDING,
                decision=None,
                comments=None,
            )
            repo.create(review)

        # Get first page
        page1, count1 = repo.search(TEST_TENANT_ID, skip=0, limit=2)
        assert len(page1) == 2
        assert count1 == 5

        # Get second page
        page2, count2 = repo.search(TEST_TENANT_ID, skip=2, limit=2)
        assert len(page2) == 2
        assert count2 == 5

    def test_tenant_isolation(self, review_repository):
        """Test that reviews are isolated per tenant."""
        repo = review_repository
        tenant1 = "tenant-1"
        tenant2 = "tenant-2"

        # Create reviews for different tenants
        review1 = Review(
            id=str(uuid.uuid4()),
            tenant_id=tenant1,
            sample_id=str(uuid.uuid4()),
            reviewer_user_id=None,
            state=ReviewState.PENDING,
            decision=None,
            comments=None,
        )
        review2 = Review(
            id=str(uuid.uuid4()),
            tenant_id=tenant2,
            sample_id=str(uuid.uuid4()),
            reviewer_user_id=None,
            state=ReviewState.PENDING,
            decision=None,
            comments=None,
        )

        repo.create(review1)
        repo.create(review2)

        # List for tenant1 should only return tenant1 reviews
        tenant1_reviews, count1 = repo.list_by_tenant(tenant1)
        assert len(tenant1_reviews) == 1
        assert tenant1_reviews[0].tenant_id == tenant1
        assert count1 == 1

        # List for tenant2 should only return tenant2 reviews
        tenant2_reviews, count2 = repo.list_by_tenant(tenant2)
        assert len(tenant2_reviews) == 1
        assert tenant2_reviews[0].tenant_id == tenant2
        assert count2 == 1

    def test_review_states(self, review_repository):
        """Test creating reviews in different states."""
        repo = review_repository

        states = [
            ReviewState.PENDING,
            ReviewState.IN_PROGRESS,
            ReviewState.APPROVED,
            ReviewState.REJECTED,
            ReviewState.ESCALATED,
        ]

        for state in states:
            review = Review(
                id=str(uuid.uuid4()),
                tenant_id=TEST_TENANT_ID,
                sample_id=str(uuid.uuid4()),
                reviewer_user_id=None,
                state=state,
                decision=None,
                comments=None,
            )
            created = repo.create(review)
            assert created.state == state

    def test_date_range_filtering(self, review_repository):
        """Test filtering reviews by date range."""
        repo = review_repository

        # Create reviews with current timestamp
        now = datetime.utcnow()

        review = Review(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            sample_id=str(uuid.uuid4()),
            reviewer_user_id=None,
            state=ReviewState.PENDING,
            decision=None,
            comments=None,
        )
        repo.create(review)

        # Search within date range (should include the review)
        start_date = now - timedelta(hours=1)
        end_date = now + timedelta(hours=1)
        results, count = repo.list_by_tenant(
            TEST_TENANT_ID, start_date=start_date, end_date=end_date
        )

        assert len(results) == 1
        assert count == 1

        # Search outside date range (should exclude the review)
        past_start = now - timedelta(days=2)
        past_end = now - timedelta(days=1)
        results, count = repo.list_by_tenant(
            TEST_TENANT_ID, start_date=past_start, end_date=past_end
        )

        assert len(results) == 0
        assert count == 0
