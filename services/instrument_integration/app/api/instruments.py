"""Instrument management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
import uuid

from app.models import Instrument, InstrumentStatus, InstrumentType
from app.services import InstrumentService
from app.dependencies import get_instrument_service
from app.exceptions import InstrumentNotFoundError, InstrumentAlreadyExistsError

router = APIRouter()

# Default tenant ID for testing (in real app, would come from JWT)
TEST_TENANT_ID = "test-tenant-123"


@router.post("/instruments/register", response_model=dict)
async def register_instrument(
    name: str,
    instrument_type: InstrumentType,
    api_token: Optional[str] = None,
    service: InstrumentService = Depends(get_instrument_service)
):
    """Register a new instrument."""
    try:
        instrument = service.create_instrument(
            tenant_id=TEST_TENANT_ID,
            name=name,
            instrument_type=instrument_type,
            api_token=api_token
        )
        return {
            "instrument_id": instrument.id,
            "name": instrument.name,
            "api_token": instrument.api_token,
            "status": instrument.status
        }
    except InstrumentAlreadyExistsError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/instruments", response_model=List[dict])
async def list_instruments(
    service: InstrumentService = Depends(get_instrument_service)
):
    """List all instruments for tenant."""
    instruments = service.list_instruments(tenant_id=TEST_TENANT_ID)
    return [
        {
            "id": i.id,
            "name": i.name,
            "instrument_type": i.instrument_type,
            "status": i.status,
            "last_successful_query_at": i.last_successful_query_at,
            "last_successful_result_at": i.last_successful_result_at,
        }
        for i in instruments
    ]


@router.get("/instruments/{instrument_id}", response_model=dict)
async def get_instrument(
    instrument_id: str,
    service: InstrumentService = Depends(get_instrument_service)
):
    """Get instrument by ID."""
    try:
        instrument = service.get_instrument(
            tenant_id=TEST_TENANT_ID,
            instrument_id=instrument_id
        )
        return {
            "id": instrument.id,
            "name": instrument.name,
            "instrument_type": instrument.instrument_type,
            "status": instrument.status,
            "api_token": instrument.api_token,
            "connection_failure_count": instrument.connection_failure_count,
            "last_failure_at": instrument.last_failure_at,
            "last_failure_reason": instrument.last_failure_reason,
        }
    except InstrumentNotFoundError:
        raise HTTPException(status_code=404, detail="Instrument not found")


@router.get("/instruments/{instrument_id}/status", response_model=dict)
async def get_instrument_status(
    instrument_id: str,
    service: InstrumentService = Depends(get_instrument_service)
):
    """Get instrument connection status."""
    try:
        instrument = service.get_instrument(
            tenant_id=TEST_TENANT_ID,
            instrument_id=instrument_id
        )
        return {
            "status": instrument.status,
            "last_successful_query_at": instrument.last_successful_query_at,
            "last_successful_result_at": instrument.last_successful_result_at,
            "connection_failure_count": instrument.connection_failure_count,
            "is_healthy": instrument.connection_failure_count < 3
        }
    except InstrumentNotFoundError:
        raise HTTPException(status_code=404, detail="Instrument not found")


@router.put("/instruments/{instrument_id}", response_model=dict)
async def update_instrument(
    instrument_id: str,
    name: Optional[str] = None,
    instrument_type: Optional[InstrumentType] = None,
    status: Optional[InstrumentStatus] = None,
    service: InstrumentService = Depends(get_instrument_service)
):
    """Update instrument configuration."""
    try:
        instrument = service.update_instrument(
            tenant_id=TEST_TENANT_ID,
            instrument_id=instrument_id,
            name=name,
            instrument_type=instrument_type,
            status=status
        )
        return {
            "id": instrument.id,
            "name": instrument.name,
            "instrument_type": instrument.instrument_type,
            "status": instrument.status,
            "updated_at": instrument.updated_at
        }
    except InstrumentNotFoundError:
        raise HTTPException(status_code=404, detail="Instrument not found")


@router.delete("/instruments/{instrument_id}", status_code=204)
async def deactivate_instrument(
    instrument_id: str,
    service: InstrumentService = Depends(get_instrument_service)
):
    """Deactivate an instrument."""
    try:
        service.delete_instrument(
            tenant_id=TEST_TENANT_ID,
            instrument_id=instrument_id
        )
    except InstrumentNotFoundError:
        raise HTTPException(status_code=404, detail="Instrument not found")


@router.post("/instruments/{instrument_id}/regenerate-token", response_model=dict)
async def regenerate_token(
    instrument_id: str,
    service: InstrumentService = Depends(get_instrument_service)
):
    """Regenerate API token for instrument."""
    try:
        instrument = service.regenerate_api_token(
            tenant_id=TEST_TENANT_ID,
            instrument_id=instrument_id
        )
        return {
            "instrument_id": instrument.id,
            "api_token": instrument.api_token,
            "api_token_created_at": instrument.api_token_created_at
        }
    except InstrumentNotFoundError:
        raise HTTPException(status_code=404, detail="Instrument not found")
