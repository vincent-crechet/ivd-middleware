"""Instrument Adapter port for abstraction of instrument communication."""

import abc
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class QueryHostRequest:
    """Request from instrument querying for pending orders."""
    patient_id: Optional[str] = None
    sample_barcode: Optional[str] = None


@dataclass
class QueryHostResponse:
    """Response with pending orders for instrument."""
    orders: List[Dict[str, Any]]
    query_timestamp: datetime
    instrument_status: str


@dataclass
class ResultRequest:
    """Result data from instrument."""
    external_instrument_result_id: str
    test_code: str
    test_name: str
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range_low: Optional[float] = None
    reference_range_high: Optional[float] = None
    collection_timestamp: Optional[datetime] = None
    instrument_flags: Optional[str] = None


@dataclass
class ResultResponse:
    """Response to result submission."""
    result_id: str
    status: str  # "accepted" or "rejected"
    verification_queued: bool
    error_message: Optional[str] = None


class IInstrumentAdapter(abc.ABC):
    """
    Port: Abstract adapter for instrument communication.

    Abstracts different instrument connection types and provides a
    unified interface for bidirectional communication.
    """

    @abc.abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """
        Test the instrument connection and return status.

        Returns:
            Dict with connection status information
        """
        pass

    @abc.abstractmethod
    def get_pending_orders(
        self,
        tenant_id: str,
        instrument_id: str,
        patient_id: Optional[str] = None,
        sample_barcode: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get pending orders for instrument query.

        Args:
            tenant_id: Tenant identifier
            instrument_id: Instrument identifier
            patient_id: Optional patient ID filter
            sample_barcode: Optional sample barcode filter

        Returns:
            List of pending orders
        """
        pass

    @abc.abstractmethod
    def process_result(
        self,
        tenant_id: str,
        instrument_id: str,
        result_data: Dict[str, Any]
    ) -> ResultResponse:
        """
        Process incoming result from instrument.

        Args:
            tenant_id: Tenant identifier
            instrument_id: Instrument identifier
            result_data: Result data dictionary

        Returns:
            ResultResponse with result_id and status
        """
        pass
