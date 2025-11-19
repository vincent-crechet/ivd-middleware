"""Mock LIS adapter for testing and development."""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import uuid
import random

from app.ports.lis_adapter import (
    ILISAdapter,
    LISConnectionStatus,
    SampleData,
    ResultData,
    SendResultsStatus,
)


class MockLISAdapter(ILISAdapter):
    """
    Mock LIS adapter that generates realistic test data.

    Useful for development, demos, and testing without needing actual LIS connection.
    """

    def __init__(self):
        """Initialize mock adapter with test data generators."""
        self._is_connected = True
        self._sent_results: List[Dict[str, Any]] = []
        self._acknowledged_result_ids: set[str] = set()
        self._sample_counter = 0
        self._result_counter = 0

    # ==================== Connection Management ====================

    def test_connection(self) -> LISConnectionStatus:
        """Test mock connection (always succeeds)."""
        return LISConnectionStatus(
            is_connected=self._is_connected,
            last_tested_at=datetime.utcnow(),
            error_message=None,
            details={"adapter": "mock", "type": "test_data_generator"}
        )

    # ==================== Receive Side (Inbound) ====================

    def get_samples(self, since: Optional[datetime] = None) -> List[SampleData]:
        """
        Generate realistic test samples.

        Args:
            since: Optional datetime (ignored for mock adapter)

        Returns:
            List of generated SampleData
        """
        samples = []

        # Generate 5 test samples
        for i in range(5):
            self._sample_counter += 1
            sample_id = f"LIS-SAMPLE-{self._sample_counter:05d}"

            # Random patient ID
            patient_id = f"PAT{random.randint(1000, 9999)}"

            # Specimen types
            specimen_types = ["blood", "urine", "serum", "plasma", "cerebrospinal fluid"]

            # Collection date within last 7 days
            collection_date = datetime.utcnow() - timedelta(days=random.randint(0, 7))
            received_date = collection_date + timedelta(hours=random.randint(0, 4))

            samples.append(SampleData(
                external_lis_id=sample_id,
                patient_id=patient_id,
                specimen_type=random.choice(specimen_types),
                collection_date=collection_date,
                received_date=received_date
            ))

        return samples

    def get_results(self, sample_external_lis_id: str) -> List[ResultData]:
        """
        Generate realistic test results for a sample.

        Args:
            sample_external_lis_id: Sample external ID

        Returns:
            List of generated ResultData
        """
        results = []

        # Generate 3-5 test results per sample
        num_results = random.randint(3, 5)

        for i in range(num_results):
            self._result_counter += 1
            result_id = f"LIS-RESULT-{self._result_counter:05d}"

            # Test codes and names
            tests = [
                ("GLU", "Glucose"),
                ("WBC", "White Blood Cell"),
                ("RBC", "Red Blood Cell"),
                ("HGB", "Hemoglobin"),
                ("HCT", "Hematocrit"),
                ("PLT", "Platelets"),
                ("NA", "Sodium"),
                ("K", "Potassium"),
                ("CL", "Chloride"),
            ]

            test_code, test_name = random.choice(tests)

            # Generate realistic values
            values = {
                "GLU": ("95", "mg/dL", 70, 100),
                "WBC": ("7.2", "K/uL", 4.5, 11.0),
                "RBC": ("4.8", "M/uL", 4.2, 5.4),
                "HGB": ("14.5", "g/dL", 13.5, 17.5),
                "HCT": ("43.2", "%", 38, 54),
                "PLT": ("250", "K/uL", 150, 400),
                "NA": ("138", "mEq/L", 135, 145),
                "K": ("4.2", "mEq/L", 3.5, 5.0),
                "CL": ("102", "mEq/L", 98, 107),
            }

            if test_code in values:
                value, unit, low, high = values[test_code]
            else:
                value = str(random.randint(50, 150))
                unit = "units"
                low = 0
                high = 200

            # Random flags (rare)
            lis_flags = None
            if random.random() < 0.1:
                lis_flags = random.choice(["H", "L", "C"])

            results.append(ResultData(
                external_lis_result_id=result_id,
                sample_external_lis_id=sample_external_lis_id,
                test_code=test_code,
                test_name=test_name,
                value=value,
                unit=unit,
                reference_range_low=float(low),
                reference_range_high=float(high),
                lis_flags=lis_flags
            ))

        return results

    # ==================== Send Side (Outbound) ====================

    def send_results(self, results: List[Dict[str, Any]]) -> SendResultsStatus:
        """
        Mock sending results to LIS (always succeeds).

        Args:
            results: List of result data dictionaries

        Returns:
            SendResultsStatus indicating success
        """
        if not self._is_connected:
            return SendResultsStatus(
                total_sent=0,
                total_failed=len(results),
                failed_result_ids=[r.get("external_lis_result_id", "") for r in results],
                retry_scheduled=True,
                next_retry_at=datetime.utcnow() + timedelta(minutes=1),
                error_message="Mock adapter is disconnected"
            )

        # Mock: all results sent successfully
        for result in results:
            self._sent_results.append({
                **result,
                "sent_at": datetime.utcnow()
            })

        return SendResultsStatus(
            total_sent=len(results),
            total_failed=0,
            failed_result_ids=[],
            retry_scheduled=False,
            error_message=None
        )

    def acknowledge_results(self, result_ids: List[str]) -> bool:
        """
        Mock acknowledging results.

        Args:
            result_ids: List of result IDs to acknowledge

        Returns:
            Always True for mock adapter
        """
        for result_id in result_ids:
            self._acknowledged_result_ids.add(result_id)

        return True

    # ==================== Mock Control Methods ====================

    def set_connection_status(self, is_connected: bool):
        """Set mock connection status for testing failure scenarios."""
        self._is_connected = is_connected

    def get_sent_results(self) -> List[Dict[str, Any]]:
        """Get all results that were sent in this session."""
        return self._sent_results.copy()

    def get_acknowledged_results(self) -> set[str]:
        """Get all result IDs that were acknowledged."""
        return self._acknowledged_result_ids.copy()

    def reset(self):
        """Reset mock adapter state."""
        self._is_connected = True
        self._sent_results.clear()
        self._acknowledged_result_ids.clear()
        self._sample_counter = 0
        self._result_counter = 0
