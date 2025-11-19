"""Review API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.services import ReviewService
from app.models import ReviewState
from app.dependencies import get_review_service, get_current_tenant_id, get_current_user
from app.exceptions import (
    ReviewNotFoundError,
    ReviewAlreadyExistsError,
    ReviewCannotBeModifiedError,
    ReviewStateTransitionError,
    ResultNotFoundError,
    SampleNotFoundError,
    InvalidReviewDecisionError,
    InsufficientPermissionError,
)


# Request/Response Models
class ReviewCreate(BaseModel):
    """Request model for creating a review."""

    sample_id: str = Field(..., description="Sample ID requiring review")
    reviewer_user_id: Optional[str] = Field(
        None,
        description="Optional user ID to assign review to. If not provided, review goes to queue."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "sample_id": "sample-123",
                "reviewer_user_id": "user-456"
            }
        }


class ApprovalRequest(BaseModel):
    """Request model for approving a sample or result."""

    comments: Optional[str] = Field(None, description="Optional approval comments")

    class Config:
        json_schema_extra = {
            "example": {
                "comments": "All results within expected ranges"
            }
        }


class RejectionRequest(BaseModel):
    """Request model for rejecting a sample or result."""

    comments: str = Field(..., description="Rejection reason (required)")

    class Config:
        json_schema_extra = {
            "example": {
                "comments": "Values inconsistent with patient history"
            }
        }


class EscalationRequest(BaseModel):
    """Request model for escalating a review."""

    reason: str = Field(..., description="Escalation reason (required)")

    class Config:
        json_schema_extra = {
            "example": {
                "reason": "Complex case requires pathologist expertise"
            }
        }


class ResultApprovalRequest(BaseModel):
    """Request model for approving an individual result."""

    result_id: str = Field(..., description="Result ID to approve")
    comments: Optional[str] = Field(None, description="Optional approval comments")

    class Config:
        json_schema_extra = {
            "example": {
                "result_id": "result-789",
                "comments": "Result confirmed with repeat testing"
            }
        }


class ResultRejectionRequest(BaseModel):
    """Request model for rejecting an individual result."""

    result_id: str = Field(..., description="Result ID to reject")
    comments: str = Field(..., description="Rejection reason (required)")

    class Config:
        json_schema_extra = {
            "example": {
                "result_id": "result-789",
                "comments": "Suspected instrument error"
            }
        }


class ResultDecisionResponse(BaseModel):
    """Response model for a result decision."""

    decision_id: str
    result_id: str
    decision: str
    comments: Optional[str]
    decided_at: str


class ReviewResponse(BaseModel):
    """Response model for a review with all details."""

    review_id: str
    sample_id: str
    reviewer_user_id: Optional[str]
    state: str
    decision: Optional[str]
    comments: Optional[str]
    escalation_reason: Optional[str]
    created_at: str
    submitted_at: Optional[str]
    completed_at: Optional[str]
    updated_at: str
    result_decisions: List[ResultDecisionResponse]


class ReviewQueueItem(BaseModel):
    """Response model for a review queue item (summary)."""

    review_id: str
    sample_id: str
    reviewer_user_id: Optional[str]
    state: str
    decision: Optional[str]
    created_at: str
    submitted_at: Optional[str]


class ReviewQueueResponse(BaseModel):
    """Response model for review queue list."""

    reviews: List[ReviewQueueItem]
    total: int
    skip: int
    limit: int


class ReviewCreateResponse(BaseModel):
    """Response model for created review."""

    review_id: str
    sample_id: str
    reviewer_user_id: Optional[str]
    state: str
    created_at: str


class ReviewActionResponse(BaseModel):
    """Response model for review actions (approve/reject/escalate)."""

    review_id: str
    state: str
    decision: Optional[str]
    message: str


class ResultDecisionActionResponse(BaseModel):
    """Response model for result decision actions."""

    decision_id: str
    result_id: str
    decision: str
    message: str


# Router
reviews_router = APIRouter(
    prefix="/api/v1/reviews",
    tags=["reviews"]
)


def require_reviewer_role(user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to ensure user has reviewer or higher role.

    Valid roles: admin, pathologist, reviewer

    Args:
        user: Current authenticated user

    Returns:
        User dict if authorized

    Raises:
        HTTPException: If user doesn't have appropriate role
    """
    valid_roles = ["admin", "administrator", "pathologist", "reviewer"]
    if user.get("role") not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Reviewer role or higher required."
        )
    return user


def require_pathologist_role(user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to ensure user has pathologist or admin role.

    Args:
        user: Current authenticated user

    Returns:
        User dict if authorized

    Raises:
        HTTPException: If user doesn't have appropriate role
    """
    valid_roles = ["admin", "administrator", "pathologist"]
    if user.get("role") not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Pathologist role or higher required."
        )
    return user


@reviews_router.get(
    "/queue",
    response_model=ReviewQueueResponse,
    status_code=status.HTTP_200_OK,
    summary="Get review queue",
    description="Get queue of samples needing review with optional filtering."
)
async def get_review_queue(
    review_service: ReviewService = Depends(get_review_service),
    tenant_id: str = Depends(get_current_tenant_id),
    user: dict = Depends(require_reviewer_role),
    state: Optional[ReviewState] = Query(None, description="Filter by review state"),
    assigned_to_me: bool = Query(False, description="Show only reviews assigned to current user"),
    escalated: bool = Query(False, description="Show only escalated reviews"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of records to return"),
):
    """
    Get review queue for current user.

    Returns list of samples needing review with optional filtering.
    Results are sorted by creation date (oldest first).

    Query parameters:
    - state: Filter by review state (pending, in_progress, escalated)
    - assigned_to_me: Show only reviews assigned to current user
    - escalated: Show only reviews escalated to pathologist
    - skip: Pagination offset
    - limit: Maximum records to return

    Returns:
        Paginated list of reviews in queue
    """
    try:
        # Determine reviewer filter
        reviewer_user_id = None
        if assigned_to_me:
            reviewer_user_id = user.get("user_id")

        result = review_service.list_review_queue(
            tenant_id=tenant_id,
            state=state,
            reviewer_user_id=reviewer_user_id,
            escalated_only=escalated,
            skip=skip,
            limit=limit,
        )

        queue_items = [
            ReviewQueueItem(
                review_id=r["review_id"],
                sample_id=r["sample_id"],
                reviewer_user_id=r["reviewer_user_id"],
                state=r["state"],
                decision=r["decision"],
                created_at=r["created_at"],
                submitted_at=r["submitted_at"],
            )
            for r in result["reviews"]
        ]

        return ReviewQueueResponse(
            reviews=queue_items,
            total=result["total"],
            skip=result["skip"],
            limit=result["limit"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving review queue: {str(e)}"
        )


@reviews_router.get(
    "/{review_id}",
    response_model=ReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get review details",
    description="Get complete review details including all result decisions."
)
async def get_review(
    review_id: str,
    review_service: ReviewService = Depends(get_review_service),
    tenant_id: str = Depends(get_current_tenant_id),
    user: dict = Depends(require_reviewer_role),
):
    """
    Get review details including all result decisions.

    Returns complete review information including:
    - Review metadata and status
    - All result decisions made
    - Reviewer comments and escalation reasons

    Args:
        review_id: Review identifier

    Returns:
        Complete review details

    Raises:
        404: If review not found
    """
    try:
        review_data = review_service.get_review(review_id, tenant_id)

        result_decisions = [
            ResultDecisionResponse(
                decision_id=d["decision_id"],
                result_id=d["result_id"],
                decision=d["decision"],
                comments=d["comments"],
                decided_at=d["decided_at"],
            )
            for d in review_data["result_decisions"]
        ]

        return ReviewResponse(
            review_id=review_data["review_id"],
            sample_id=review_data["sample_id"],
            reviewer_user_id=review_data["reviewer_user_id"],
            state=review_data["state"],
            decision=review_data["decision"],
            comments=review_data["comments"],
            escalation_reason=review_data["escalation_reason"],
            created_at=review_data["created_at"],
            submitted_at=review_data["submitted_at"],
            completed_at=review_data["completed_at"],
            updated_at=review_data["updated_at"],
            result_decisions=result_decisions,
        )

    except ReviewNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving review: {str(e)}"
        )


@reviews_router.post(
    "",
    response_model=ReviewCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create review",
    description="Create a new review for a sample."
)
async def create_review(
    request: ReviewCreate,
    review_service: ReviewService = Depends(get_review_service),
    tenant_id: str = Depends(get_current_tenant_id),
    user: dict = Depends(require_reviewer_role),
):
    """
    Create a new review for a sample.

    Creates a review record for a sample that has results needing manual verification.
    Can optionally assign to a specific reviewer, otherwise goes to general queue.

    Args:
        request: Review creation data including sample_id and optional reviewer

    Returns:
        Created review record

    Raises:
        404: If sample not found
        409: If review already exists for this sample
    """
    try:
        review = review_service.create_review(
            tenant_id=tenant_id,
            sample_id=request.sample_id,
            reviewer_user_id=request.reviewer_user_id,
        )

        return ReviewCreateResponse(
            review_id=review.id,
            sample_id=review.sample_id,
            reviewer_user_id=review.reviewer_user_id,
            state=review.state.value,
            created_at=review.created_at.isoformat(),
        )

    except SampleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample '{request.sample_id}' not found"
        )
    except ReviewAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Review already exists for sample '{request.sample_id}'"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating review: {str(e)}"
        )


@reviews_router.post(
    "/{review_id}/approve",
    response_model=ReviewActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve entire sample",
    description="Approve all results in the sample."
)
async def approve_sample(
    review_id: str,
    request: ApprovalRequest,
    review_service: ReviewService = Depends(get_review_service),
    tenant_id: str = Depends(get_current_tenant_id),
    user: dict = Depends(require_reviewer_role),
):
    """
    Approve entire sample and all its results.

    Creates approval decisions for all results that need review in the sample.
    This marks the sample as verified and ready for reporting.

    Args:
        review_id: Review identifier
        request: Approval request with optional comments

    Returns:
        Updated review status

    Raises:
        404: If review not found
        400: If review cannot be modified (already completed)
    """
    try:
        review = review_service.approve_sample(
            review_id=review_id,
            tenant_id=tenant_id,
            user_id=user.get("user_id"),
            comments=request.comments,
        )

        return ReviewActionResponse(
            review_id=review.id,
            state=review.state.value,
            decision=review.decision.value if review.decision else None,
            message=f"Sample approved successfully"
        )

    except ReviewNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review not found"
        )
    except ReviewCannotBeModifiedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ReviewStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving sample: {str(e)}"
        )


@reviews_router.post(
    "/{review_id}/reject",
    response_model=ReviewActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject entire sample",
    description="Reject the entire sample and all its results."
)
async def reject_sample(
    review_id: str,
    request: RejectionRequest,
    review_service: ReviewService = Depends(get_review_service),
    tenant_id: str = Depends(get_current_tenant_id),
    user: dict = Depends(require_reviewer_role),
):
    """
    Reject entire sample and all its results.

    Creates rejection decisions for all results that need review in the sample.
    This marks the sample as rejected and prevents reporting.
    Comments are required to document the rejection reason.

    Args:
        review_id: Review identifier
        request: Rejection request with required comments

    Returns:
        Updated review status

    Raises:
        404: If review not found
        400: If review cannot be modified or comments missing
    """
    try:
        if not request.comments or not request.comments.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection comments are required"
            )

        review = review_service.reject_sample(
            review_id=review_id,
            tenant_id=tenant_id,
            user_id=user.get("user_id"),
            comments=request.comments,
        )

        return ReviewActionResponse(
            review_id=review.id,
            state=review.state.value,
            decision=review.decision.value if review.decision else None,
            message=f"Sample rejected successfully"
        )

    except ReviewNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review not found"
        )
    except ReviewCannotBeModifiedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ReviewStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rejecting sample: {str(e)}"
        )


@reviews_router.post(
    "/{review_id}/approve-result",
    response_model=ResultDecisionActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve individual result",
    description="Approve a specific result within the review."
)
async def approve_result(
    review_id: str,
    request: ResultApprovalRequest,
    review_service: ReviewService = Depends(get_review_service),
    tenant_id: str = Depends(get_current_tenant_id),
    user: dict = Depends(require_reviewer_role),
):
    """
    Approve an individual result within a review.

    Creates an approval decision for a specific result.
    The review will be automatically completed if all results have been decided.

    Args:
        review_id: Review identifier
        request: Result approval request with result_id and optional comments

    Returns:
        Created result decision

    Raises:
        404: If review or result not found
        400: If review cannot be modified or result doesn't belong to sample
    """
    try:
        decision = review_service.approve_result(
            review_id=review_id,
            result_id=request.result_id,
            tenant_id=tenant_id,
            user_id=user.get("user_id"),
            comments=request.comments,
        )

        return ResultDecisionActionResponse(
            decision_id=decision.id,
            result_id=decision.result_id,
            decision=decision.decision,
            message=f"Result approved successfully"
        )

    except ReviewNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review not found"
        )
    except ResultNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result '{request.result_id}' not found"
        )
    except ReviewCannotBeModifiedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except InvalidReviewDecisionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error approving result: {str(e)}"
        )


@reviews_router.post(
    "/{review_id}/reject-result",
    response_model=ResultDecisionActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject individual result",
    description="Reject a specific result within the review."
)
async def reject_result(
    review_id: str,
    request: ResultRejectionRequest,
    review_service: ReviewService = Depends(get_review_service),
    tenant_id: str = Depends(get_current_tenant_id),
    user: dict = Depends(require_reviewer_role),
):
    """
    Reject an individual result within a review.

    Creates a rejection decision for a specific result.
    The review will be automatically completed if all results have been decided.
    Comments are required to document the rejection reason.

    Args:
        review_id: Review identifier
        request: Result rejection request with result_id and required comments

    Returns:
        Created result decision

    Raises:
        404: If review or result not found
        400: If review cannot be modified, comments missing, or result doesn't belong to sample
    """
    try:
        if not request.comments or not request.comments.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rejection comments are required"
            )

        decision = review_service.reject_result(
            review_id=review_id,
            result_id=request.result_id,
            tenant_id=tenant_id,
            user_id=user.get("user_id"),
            comments=request.comments,
        )

        return ResultDecisionActionResponse(
            decision_id=decision.id,
            result_id=decision.result_id,
            decision=decision.decision,
            message=f"Result rejected successfully"
        )

    except ReviewNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review not found"
        )
    except ResultNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Result '{request.result_id}' not found"
        )
    except ReviewCannotBeModifiedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except InvalidReviewDecisionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error rejecting result: {str(e)}"
        )


@reviews_router.post(
    "/{review_id}/escalate",
    response_model=ReviewActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Escalate review to pathologist",
    description="Escalate a review to pathologist for expert review."
)
async def escalate_review(
    review_id: str,
    request: EscalationRequest,
    review_service: ReviewService = Depends(get_review_service),
    tenant_id: str = Depends(get_current_tenant_id),
    user: dict = Depends(require_reviewer_role),
):
    """
    Escalate a review to pathologist for expert review.

    Marks the review as escalated and moves it to the pathologist queue.
    Reason is required to document why escalation is needed.

    Args:
        review_id: Review identifier
        request: Escalation request with required reason

    Returns:
        Updated review status

    Raises:
        404: If review not found
        400: If review cannot be modified or reason missing
    """
    try:
        if not request.reason or not request.reason.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Escalation reason is required"
            )

        review = review_service.escalate_review(
            review_id=review_id,
            tenant_id=tenant_id,
            user_id=user.get("user_id"),
            reason=request.reason,
        )

        return ReviewActionResponse(
            review_id=review.id,
            state=review.state.value,
            decision=review.decision.value if review.decision else None,
            message=f"Review escalated to pathologist successfully"
        )

    except ReviewNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review not found"
        )
    except ReviewCannotBeModifiedError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except ReviewStateTransitionError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error escalating review: {str(e)}"
        )
