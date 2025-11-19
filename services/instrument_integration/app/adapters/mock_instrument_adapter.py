"""Mock instrument adapter for testing and development."""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import random

from app.ports.instrument_adapter import IInstrumentAdapter, ResultResponse


class MockInstrumentAdapter(IInstrumentAdapter):
    """
    Mock instrument adapter that simulates real instrument behavior.

    Useful for development and testing without needing actual instrument connection.
    """

    def __init__(self):
        """Initialize mock adapter with test data generators."""
        self._is_connected = True
        self._query_counter = 0
        self._result_counter = 0
        self._processed_results: List[Dict[str, Any]] = []

    def test_connection(self) -> Dict[str, Any]:
        """Test mock connection (always succeeds)."""
        return {
            "is_connected": self._is_connected,
            "last_tested_at": datetime.utcnow(),
            "adapter": "mock",
            "type": "test_data_generator"
        }

    def get_pending_orders(
        self,
        tenant_id: str,
        instrument_id: str,
        patient_id: Optional[str] = None,
        sample_barcode: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate realistic pending orders for instrument.

        Args:
            tenant_id: Tenant identifier
            instrument_id: Instrument identifier
            patient_id: Optional patient ID filter
            sample_barcode: Optional sample barcode filter

        Returns:
            List of pending orders
        """
        if not self._is_connected:
            return []

        self._query_counter += 1
        orders = []

        # Generate 2-4 mock orders
        for i in range(random.randint(2, 4)):
            self._result_counter += 1
            test_codes = ["GLU", "WBC", "RBC", "HGB", "HCT", "PLT"]
            
            order = {
                "order_id": f"ORDER-{self._query_counter}-{i+1}",
                "external_lis_order_id": f"LIS-ORDER-{uuid.uuid4().hex[:8]}",
                "patient_id": patient_id or f"PAT{random.randint(1000, 9999)}",
                "sample_id": f"SAMPLE-{self._result_counter:05d}",
                "test_codes": ",".join(random.sample(test_codes, random.randint(1, 3))),
                "priority": random.choice(["routine", "stat", "critical"]),
                "created_at": datetime.utcnow().isoformat(),
            }
            orders.append(order)

        return orders

    def process_result(
        self,
        tenant_id: str,
        instrument_id: str,
        result_data: Dict[str, Any]
    ) -> ResultResponse:
        """
        Mock processing of result from instrument.

        Args:
            tenant_id: Tenant identifier
            instrument_id: Instrument identifier
            result_data: Result data dictionary

        Returns:
            ResultResponse indicating success
        """
        if not self._is_connected:
            return ResultResponse(
                result_id="",
                status="rejected",
                verification_queued=False,
                error_message="Mock adapter is disconnected"
            )

        result_id = f"RESULT-{uuid.uuid4().hex[:8]}"
        
        self._processed_results.append({
            **result_data,
            "result_id": result_id,
            "processed_at": datetime.utcnow()
        })

        return ResultResponse(
            result_id=result_id,
            status="accepted",
            verification_queued=True
        )

    # Mock control methods
    def set_connection_status(self, is_connected: bool):
        """Set mock connection status for testing failure scenarios."""
        self._is_connected = is_connected

    def get_processed_results(self) -> List[Dict[str, Any]]:
        """Get all results that were processed in this session."""
        return self._processed_results.copy()

    def reset(self):
        """Reset mock adapter state."""
        self._is_connected = True
        self._processed_results.clear()
        self._query_counter = 0
        self._result_counter = 0
