"""Result API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional

from app.services import ResultService, SampleService
from app.models import ResultStatus, UploadStatus
from app.dependencies import get_result_service, get_sample_service, get_current_tenant_id
from app.exceptions import ResultNotFoundError, SampleNotFoundError

results_router = APIRouter(prefix="/results", tags=["results"])


@results_router.get("")
async def list_results(
    result_service: ResultService = Depends(get_result_service),
    tenant_id: str = Depends(get_current_tenant_id),
    status: Optional[ResultStatus] = Query(None, description="Verification status"),
    upload_status: Optional[UploadStatus] = Query(None, description="Upload status"),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Records to return"),
):
    """
    List results for tenant with optional filtering.

    Results sorted by creation date (newest first).
    """
    try:
        results, total = result_service.search_results(
            tenant_id=tenant_id,
            status=status,
            upload_status=upload_status,
            skip=skip,
            limit=limit
        )

        return {
            "items": [
                {
                    "id": r.id,
                    "sample_id": r.sample_id,
                    "external_lis_result_id": r.external_lis_result_id,
                    "test_code": r.test_code,
                    "test_name": r.test_name,
                    "value": r.value,
                    "unit": r.unit,
                    "reference_range_low": r.reference_range_low,
                    "reference_range_high": r.reference_range_high,
                    "lis_flags": r.lis_flags,
                    "verification_status": r.verification_status,
                    "verification_method": r.verification_method,
                    "upload_status": r.upload_status,
                    "created_at": r.created_at.isoformat(),
                }
                for r in results
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing results: {str(e)}"
        )


@results_router.get("/{result_id}")
async def get_result(
    result_id: str,
    result_service: ResultService = Depends(get_result_service),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get result details by ID."""
    try:
        result = result_service.get_result(result_id, tenant_id)

        return {
            "id": result.id,
            "sample_id": result.sample_id,
            "external_lis_result_id": result.external_lis_result_id,
            "test_code": result.test_code,
            "test_name": result.test_name,
            "value": result.value,
            "unit": result.unit,
            "reference_range_low": result.reference_range_low,
            "reference_range_high": result.reference_range_high,
            "lis_flags": result.lis_flags,
            "verification_status": result.verification_status,
            "verification_method": result.verification_method,
            "verified_at": result.verified_at.isoformat() if result.verified_at else None,
            "upload_status": result.upload_status,
            "sent_to_lis_at": result.sent_to_lis_at.isoformat() if result.sent_to_lis_at else None,
            "upload_failure_count": result.upload_failure_count,
            "upload_failure_reason": result.upload_failure_reason,
            "created_at": result.created_at.isoformat(),
            "updated_at": result.updated_at.isoformat(),
        }
    except ResultNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving result: {str(e)}"
        )


@results_router.get("/sample/{sample_id}")
async def get_results_for_sample(
    sample_id: str,
    result_service: ResultService = Depends(get_result_service),
    sample_service: SampleService = Depends(get_sample_service),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get all results for a specific sample."""
    try:
        # Verify sample exists
        sample_service.get_sample(sample_id, tenant_id)

        # Get results
        results = result_service.list_results_by_sample(sample_id, tenant_id)

        return {
            "sample_id": sample_id,
            "items": [
                {
                    "id": r.id,
                    "external_lis_result_id": r.external_lis_result_id,
                    "test_code": r.test_code,
                    "test_name": r.test_name,
                    "value": r.value,
                    "unit": r.unit,
                    "verification_status": r.verification_status,
                    "upload_status": r.upload_status,
                    "created_at": r.created_at.isoformat(),
                }
                for r in results
            ],
            "total": len(results),
        }
    except SampleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sample not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving results: {str(e)}"
        )
