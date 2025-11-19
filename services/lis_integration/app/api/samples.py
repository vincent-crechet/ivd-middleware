"""Sample API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from datetime import datetime
from typing import Optional

from app.services import SampleService
from app.models import SampleStatus
from app.dependencies import get_sample_service, get_current_tenant_id
from app.exceptions import SampleNotFoundError

samples_router = APIRouter(prefix="/samples", tags=["samples"])


@samples_router.get("")
async def list_samples(
    sample_service: SampleService = Depends(get_sample_service),
    tenant_id: str = Depends(get_current_tenant_id),
    patient_id: Optional[str] = Query(None, description="Patient ID partial match"),
    start_date: Optional[datetime] = Query(None, description="Collection date start"),
    end_date: Optional[datetime] = Query(None, description="Collection date end"),
    status: Optional[SampleStatus] = Query(None, description="Sample status"),
    specimen_type: Optional[str] = Query(None, description="Specimen type"),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Records to return"),
):
    """
    List samples for tenant with optional filtering.

    Query filters are all optional. Results sorted by collection_date (newest first).
    """
    try:
        samples, total = sample_service.search_samples(
            tenant_id=tenant_id,
            patient_id=patient_id,
            start_date=start_date,
            end_date=end_date,
            status=status,
            specimen_type=specimen_type,
            skip=skip,
            limit=limit
        )

        return {
            "items": [
                {
                    "id": s.id,
                    "external_lis_id": s.external_lis_id,
                    "patient_id": s.patient_id,
                    "specimen_type": s.specimen_type,
                    "collection_date": s.collection_date.isoformat(),
                    "received_date": s.received_date.isoformat(),
                    "status": s.status,
                    "created_at": s.created_at.isoformat(),
                }
                for s in samples
            ],
            "total": total,
            "skip": skip,
            "limit": limit,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing samples: {str(e)}"
        )


@samples_router.get("/{sample_id}")
async def get_sample(
    sample_id: str,
    sample_service: SampleService = Depends(get_sample_service),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get sample details by ID."""
    try:
        sample = sample_service.get_sample(sample_id, tenant_id)

        return {
            "id": sample.id,
            "external_lis_id": sample.external_lis_id,
            "patient_id": sample.patient_id,
            "specimen_type": sample.specimen_type,
            "collection_date": sample.collection_date.isoformat(),
            "received_date": sample.received_date.isoformat(),
            "status": sample.status,
            "created_at": sample.created_at.isoformat(),
            "updated_at": sample.updated_at.isoformat(),
        }
    except SampleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving sample: {str(e)}"
        )
