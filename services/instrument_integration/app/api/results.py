"""Result reception endpoints (instruments sending results)."""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import Optional
from datetime import datetime

from app.services import InstrumentService, InstrumentResultService
from app.dependencies import (
    get_instrument_service,
    get_instrument_result_service
)
from app.exceptions import (
    InvalidApiTokenError,
    InstrumentNotFoundError,
    InvalidResultDataError,
    InstrumentResultAlreadyExistsError
)

router = APIRouter()

# Default tenant ID for testing
TEST_TENANT_ID = "test-tenant-123"


@router.post("/instruments/results", status_code=202)
async def submit_result(
    external_instrument_result_id: str,
    test_code: str,
    test_name: str,
    value: Optional[str] = None,
    unit: Optional[str] = None,
    reference_range_low: Optional[float] = None,
    reference_range_high: Optional[float] = None,
    collection_timestamp: Optional[datetime] = None,
    instrument_flags: Optional[str] = None,
    x_instrument_token: Optional[str] = Header(None),
    instrument_service: InstrumentService = Depends(get_instrument_service),
    result_service: InstrumentResultService = Depends(get_instrument_result_service)
):
    """
    Instrument submits test result.

    Authentication via X-Instrument-Token header.
    Returns 202 Accepted if valid, 400 if invalid.
    """
    if not x_instrument_token:
        raise HTTPException(
            status_code=401,
            detail="Missing X-Instrument-Token header"
        )

    # Authenticate instrument via API token
    try:
        instrument = instrument_service.get_by_api_token(x_instrument_token)
    except (InvalidApiTokenError, InstrumentNotFoundError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired API token"
        )

    # Check if instrument is active
    if instrument.status.value != "active":
        raise HTTPException(
            status_code=403,
            detail="Instrument is not active"
        )

    # Use collection timestamp if provided, otherwise use current time
    if collection_timestamp is None:
        collection_timestamp = datetime.utcnow()

    try:
        # Create result
        result = result_service.create_result(
            tenant_id=TEST_TENANT_ID,
            instrument_id=instrument.id,
            external_result_id=external_instrument_result_id,
            test_code=test_code,
            test_name=test_name,
            value=value,
            unit=unit,
            reference_range_low=reference_range_low,
            reference_range_high=reference_range_high,
            collection_timestamp=collection_timestamp,
            instrument_flags=instrument_flags
        )

        # Record successful result
        instrument_service.record_successful_result(
            tenant_id=TEST_TENANT_ID,
            instrument_id=instrument.id
        )

        return {
            "result_id": result.id,
            "status": "accepted",
            "verification_queued": True
        }

    except InstrumentResultAlreadyExistsError:
        # Duplicate result - silently skip (idempotent)
        return {
            "result_id": external_instrument_result_id,
            "status": "accepted",
            "verification_queued": False,
            "message": "Result already exists (duplicate)"
        }

    except InvalidResultDataError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid result data: {str(e)}"
        )

    except Exception as e:
        # Record failure
        instrument_service.record_result_failure(
            tenant_id=TEST_TENANT_ID,
            instrument_id=instrument.id
        )

        raise HTTPException(
            status_code=400,
            detail=f"Failed to process result: {str(e)}"
        )
