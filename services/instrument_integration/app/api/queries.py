"""Host query endpoints (instruments querying for pending orders)."""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from typing import Optional
from datetime import datetime

from app.services import InstrumentService, OrderService, InstrumentQueryService
from app.dependencies import (
    get_instrument_service,
    get_order_service,
    get_instrument_query_service
)
from app.exceptions import InvalidApiTokenError, InstrumentNotFoundError
from app.models import QueryResponseStatus

router = APIRouter()

# Default tenant ID for testing
TEST_TENANT_ID = "test-tenant-123"


@router.post("/instruments/query-host", status_code=200)
async def query_host(
    patient_id: Optional[str] = None,
    sample_barcode: Optional[str] = None,
    x_instrument_token: Optional[str] = Header(None),
    instrument_service: InstrumentService = Depends(get_instrument_service),
    order_service: OrderService = Depends(get_order_service),
    query_service: InstrumentQueryService = Depends(get_instrument_query_service)
):
    """
    Instrument queries for pending test orders.

    Authentication via X-Instrument-Token header.
    Returns pending orders for the specified patient or sample.
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

    query_timestamp = datetime.utcnow()

    try:
        # Get pending orders (in real implementation, would filter by patient/sample)
        orders = order_service.list_orders(
            tenant_id=TEST_TENANT_ID,
            status="pending"
        )

        # Convert orders to response format
        orders_list = [
            {
                "order_id": o.id,
                "external_lis_order_id": o.external_lis_order_id,
                "patient_id": o.patient_id,
                "test_codes": o.test_codes,
                "priority": o.priority,
                "created_at": o.created_at.isoformat()
            }
            for o in orders
        ]

        # Record query in audit log
        query_service.record_query(
            tenant_id=TEST_TENANT_ID,
            instrument_id=instrument.id,
            patient_id=patient_id,
            sample_barcode=sample_barcode,
            orders_returned=len(orders_list),
            response_status=QueryResponseStatus.SUCCESS.value
        )

        # Record successful query
        instrument_service.record_successful_query(
            tenant_id=TEST_TENANT_ID,
            instrument_id=instrument.id
        )

        return {
            "orders": orders_list,
            "query_timestamp": query_timestamp.isoformat(),
            "instrument_status": instrument.status.value
        }

    except Exception as e:
        # Record failed query
        query_service.record_query(
            tenant_id=TEST_TENANT_ID,
            instrument_id=instrument.id,
            patient_id=patient_id,
            sample_barcode=sample_barcode,
            orders_returned=0,
            response_status=QueryResponseStatus.ERROR.value,
            error_reason=str(e)
        )

        instrument_service.record_query_failure(
            tenant_id=TEST_TENANT_ID,
            instrument_id=instrument.id,
            reason=str(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Failed to process query"
        )
