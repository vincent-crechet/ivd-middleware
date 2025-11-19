"""LIS Adapter port for abstraction of LIS communication."""

import abc
from typing import Optional, List, Dict, Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class LISConnectionStatus:
    """Status of a LIS connection."""
    is_connected: bool
    last_tested_at: datetime
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class SampleData:
    """Raw sample data from LIS adapter."""
    external_lis_id: str
    patient_id: str
    specimen_type: str
    collection_date: datetime
    received_date: datetime


@dataclass
class ResultData:
    """Raw result data from LIS adapter."""
    external_lis_result_id: str
    sample_external_lis_id: str
    test_code: str
    test_name: str
    value: Optional[str]
    unit: Optional[str]
    reference_range_low: Optional[float]
    reference_range_high: Optional[float]
    lis_flags: Optional[str]


@dataclass
class SendResultsStatus:
    """Status of sending results to LIS."""
    total_sent: int
    total_failed: int
    failed_result_ids: List[str]
    retry_scheduled: bool
    next_retry_at: Optional[datetime] = None
    error_message: Optional[str] = None


class ILISAdapter(abc.ABC):
    """
    Port: Abstract adapter for LIS communication.

    Abstracts different LIS connection types (mock, file upload, REST API, etc.)
    and provides a unified interface for bidirectional communication.
    """

    # ==================== Receive Side (Inbound) ====================

    @abc.abstractmethod
    def test_connection(self) -> LISConnectionStatus:
        """
        Test the LIS connection and return status.

        Returns:
            LISConnectionStatus with connection health information
        """
        pass

    @abc.abstractmethod
    def get_samples(self, since: Optional[datetime] = None) -> List[SampleData]:
        """
        Retrieve samples from LIS, optionally filtered by date.

        For pull model: retrieves samples since last successful retrieval
        For push model: not used (data arrives via API endpoint)

        Args:
            since: Optional datetime to retrieve only samples modified after this time

        Returns:
            List of SampleData objects

        Raises:
            LISConnectionError: If connection to LIS fails
            LISDataFormatError: If received data format is invalid
        """
        pass

    @abc.abstractmethod
    def get_results(self, sample_external_lis_id: str) -> List[ResultData]:
        """
        Retrieve results for a specific sample from LIS.

        Args:
            sample_external_lis_id: External LIS sample ID

        Returns:
            List of ResultData objects for the sample

        Raises:
            LISConnectionError: If connection to LIS fails
            LISDataFormatError: If received data format is invalid
        """
        pass

    # ==================== Send Side (Outbound) ====================

    @abc.abstractmethod
    def send_results(self, results: List[Dict[str, Any]]) -> SendResultsStatus:
        """
        Send verified/rejected results back to external LIS.

        Args:
            results: List of result data dictionaries with:
                - external_lis_result_id: Original result ID from LIS
                - verification_status: "verified" or "rejected"
                - verification_method: "auto" or "manual"
                - value: result value
                - verified_at: timestamp when verified

        Returns:
            SendResultsStatus with upload results

        Raises:
            LISConnectionError: If connection to LIS fails
            LISDataFormatError: If result data format is invalid
        """
        pass

    @abc.abstractmethod
    def acknowledge_results(self, result_ids: List[str]) -> bool:
        """
        Acknowledge that results have been received and processed.

        Used for pull model to indicate which results have been processed.

        Args:
            result_ids: List of external LIS result IDs to acknowledge

        Returns:
            True if acknowledgment successful, False otherwise

        Raises:
            LISConnectionError: If connection to LIS fails
        """
        pass
