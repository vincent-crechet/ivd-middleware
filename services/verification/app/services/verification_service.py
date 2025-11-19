"""Verification service implementation."""

import logging
from typing import Optional
from datetime import datetime

from app.ports.verification_engine import IVerificationEngine, ResultData
from app.ports.auto_verification_settings_repository import (
    IAutoVerificationSettingsRepository,
)
from app.exceptions import ResultNotFoundError, SettingsNotFoundError

# Import from LIS integration service for result management
# In production, this would be done via service-to-service communication
try:
    from services.lis_integration.app.ports.result_repository import IResultRepository
    from services.lis_integration.app.models import Result, ResultStatus
except ImportError:
    # Fallback for when running in isolation
    from typing import Protocol
    from enum import Enum

    class ResultStatus(str, Enum):
        """Result verification status."""

        PENDING = "pending"
        VERIFIED = "verified"
        NEEDS_REVIEW = "needs_review"
        REJECTED = "rejected"

    class Result(Protocol):
        """Protocol for Result model when LIS service is not available."""

        id: str
        sample_id: str
        tenant_id: str
        test_code: str
        value: Optional[str]
        unit: Optional[str]
        lis_flags: Optional[str]
        verification_status: ResultStatus
        verification_method: Optional[str]
        verified_at: Optional[datetime]

    class IResultRepository(Protocol):
        """Protocol for result repository when LIS service is not available."""

        def get_by_id(self, result_id: str, tenant_id: str) -> Optional[Result]:
            """Get result by ID."""
            ...

        def update_verification_status(
            self,
            result_id: str,
            tenant_id: str,
            status: ResultStatus,
            method: Optional[str] = None,
        ) -> Result:
            """Update verification status."""
            ...


logger = logging.getLogger(__name__)


class VerificationService:
    """
    Service for verifying test results using configured rules.

    This service orchestrates the verification process by:
    1. Loading verification settings for test codes
    2. Applying verification rules via the engine
    3. Updating result statuses based on verification outcomes
    4. Maintaining audit trails of verification decisions

    Attributes:
        settings_repository: Repository for auto-verification settings
        result_repository: Repository for test results
        verification_engine: Engine that applies verification rules
    """

    def __init__(
        self,
        settings_repository: IAutoVerificationSettingsRepository,
        result_repository: IResultRepository,
        verification_engine: IVerificationEngine,
    ):
        """
        Initialize the verification service.

        Args:
            settings_repository: Repository for accessing verification settings
            result_repository: Repository for accessing and updating results
            verification_engine: Engine for applying verification rules
        """
        self.settings_repository = settings_repository
        self.result_repository = result_repository
        self.verification_engine = verification_engine

    def verify_result(self, tenant_id: str, result_id: str) -> dict:
        """
        Verify a single result and update its status.

        Args:
            tenant_id: Tenant identifier
            result_id: Result identifier to verify

        Returns:
            Dictionary containing:
                - result_id: ID of the verified result
                - can_auto_verify: Whether result passed verification
                - verification_status: New status of the result
                - failed_rules: List of failed rule types (if any)
                - failure_reasons: Reasons for failure (if any)

        Raises:
            ResultNotFoundError: If result doesn't exist
            SettingsNotFoundError: If no settings exist for the test code
        """
        logger.info(f"Verifying result {result_id} for tenant {tenant_id}")

        # Load result
        result = self.result_repository.get_by_id(result_id, tenant_id)
        if result is None:
            raise ResultNotFoundError(
                f"Result {result_id} not found in tenant {tenant_id}"
            )

        # Convert to ResultData for verification engine
        result_data = ResultData(
            test_code=result.test_code,
            value=result.value,
            unit=result.unit,
            lis_flags=result.lis_flags,
            sample_id=result.sample_id,
            result_id=result.id,
        )

        # Apply verification rules
        decision = self.verification_engine.verify_result(result_data, tenant_id)

        # Update result status based on decision
        if decision.can_auto_verify:
            new_status = ResultStatus.VERIFIED
            method = "auto"
            logger.info(f"Result {result_id} auto-verified successfully")
        else:
            new_status = ResultStatus.NEEDS_REVIEW
            method = None  # Manual review pending
            logger.info(
                f"Result {result_id} failed auto-verification - needs manual review"
            )

        # Update result in database
        self.update_result_verification_status(
            result_id=result_id,
            tenant_id=tenant_id,
            status=new_status,
            method=method,
        )

        return {
            "result_id": result_id,
            "can_auto_verify": decision.can_auto_verify,
            "verification_status": new_status.value,
            "failed_rules": decision.failed_rules,
            "failure_reasons": decision.failure_reasons,
        }

    def verify_batch(self, tenant_id: str, result_ids: list[str]) -> dict:
        """
        Verify multiple results in batch and update their statuses.

        More efficient than calling verify_result individually as it loads
        settings and rules once for all results.

        Args:
            tenant_id: Tenant identifier
            result_ids: List of result identifiers to verify

        Returns:
            Dictionary containing:
                - total: Total number of results processed
                - verified: Number of results that passed auto-verification
                - needs_review: Number of results that need manual review
                - errors: Number of results that encountered errors
                - results: List of individual result outcomes

        Raises:
            ValueError: If result_ids is empty
        """
        logger.info(f"Batch verifying {len(result_ids)} results for tenant {tenant_id}")

        if not result_ids:
            raise ValueError("result_ids cannot be empty")

        # Load all results
        results = []
        for result_id in result_ids:
            result = self.result_repository.get_by_id(result_id, tenant_id)
            if result:
                results.append(result)
            else:
                logger.warning(
                    f"Result {result_id} not found in tenant {tenant_id} - skipping"
                )

        if not results:
            logger.warning("No valid results found to verify")
            return {
                "total": 0,
                "verified": 0,
                "needs_review": 0,
                "errors": 0,
                "results": [],
            }

        # Convert to ResultData for verification engine
        result_data_list = [
            ResultData(
                test_code=r.test_code,
                value=r.value,
                unit=r.unit,
                lis_flags=r.lis_flags,
                sample_id=r.sample_id,
                result_id=r.id,
            )
            for r in results
        ]

        # Apply verification rules in batch
        decisions = self.verification_engine.verify_batch(result_data_list, tenant_id)

        # Process each decision and update result statuses
        verified_count = 0
        needs_review_count = 0
        error_count = 0
        result_outcomes = []

        for result in results:
            try:
                decision = decisions.get(result.id)
                if decision is None:
                    logger.error(
                        f"No verification decision returned for result {result.id}"
                    )
                    error_count += 1
                    continue

                # Determine new status
                if decision.can_auto_verify:
                    new_status = ResultStatus.VERIFIED
                    method = "auto"
                    verified_count += 1
                else:
                    new_status = ResultStatus.NEEDS_REVIEW
                    method = None
                    needs_review_count += 1

                # Update result
                self.update_result_verification_status(
                    result_id=result.id,
                    tenant_id=tenant_id,
                    status=new_status,
                    method=method,
                )

                result_outcomes.append(
                    {
                        "result_id": result.id,
                        "test_code": result.test_code,
                        "can_auto_verify": decision.can_auto_verify,
                        "verification_status": new_status.value,
                        "failed_rules": decision.failed_rules,
                        "failure_reasons": decision.failure_reasons,
                    }
                )

            except Exception as e:
                logger.error(
                    f"Error processing verification for result {result.id}: {str(e)}",
                    exc_info=True,
                )
                error_count += 1

        logger.info(
            f"Batch verification complete: {verified_count} verified, "
            f"{needs_review_count} need review, {error_count} errors"
        )

        return {
            "total": len(results),
            "verified": verified_count,
            "needs_review": needs_review_count,
            "errors": error_count,
            "results": result_outcomes,
        }

    def verify_sample_results(self, tenant_id: str, sample_id: str) -> dict:
        """
        Verify all results for a sample.

        Convenience method that loads all results for a sample and verifies them.

        Args:
            tenant_id: Tenant identifier
            sample_id: Sample identifier

        Returns:
            Dictionary with same structure as verify_batch

        Raises:
            ValueError: If no results found for sample
        """
        logger.info(f"Verifying all results for sample {sample_id} in tenant {tenant_id}")

        # Load all results for sample
        results = self.result_repository.list_by_sample(sample_id, tenant_id)

        if not results:
            raise ValueError(f"No results found for sample {sample_id}")

        # Verify in batch
        result_ids = [r.id for r in results]
        return self.verify_batch(tenant_id, result_ids)

    def update_result_verification_status(
        self,
        result_id: str,
        tenant_id: str,
        status: ResultStatus,
        method: Optional[str] = None,
    ) -> None:
        """
        Update a result's verification status and method.

        Args:
            result_id: Result identifier
            tenant_id: Tenant identifier
            status: New verification status
            method: Verification method ("auto" or "manual")

        Raises:
            ResultNotFoundError: If result doesn't exist
        """
        logger.debug(
            f"Updating verification status for result {result_id} to {status.value}"
        )

        try:
            self.result_repository.update_verification_status(
                result_id=result_id,
                tenant_id=tenant_id,
                status=status,
                method=method,
            )
        except Exception as e:
            logger.error(
                f"Failed to update verification status for result {result_id}: {str(e)}",
                exc_info=True,
            )
            raise ResultNotFoundError(
                f"Failed to update result {result_id}: {str(e)}"
            ) from e

    def get_result_verification_history(
        self, tenant_id: str, result_id: str
    ) -> dict:
        """
        Get verification history and audit trail for a result.

        Args:
            tenant_id: Tenant identifier
            result_id: Result identifier

        Returns:
            Dictionary containing:
                - result_id: Result identifier
                - test_code: Test code
                - verification_status: Current verification status
                - verification_method: Method used (auto/manual)
                - verified_at: Timestamp of verification
                - value: Result value
                - lis_flags: Instrument flags

        Raises:
            ResultNotFoundError: If result doesn't exist
        """
        logger.debug(f"Getting verification history for result {result_id}")

        result = self.result_repository.get_by_id(result_id, tenant_id)
        if result is None:
            raise ResultNotFoundError(
                f"Result {result_id} not found in tenant {tenant_id}"
            )

        return {
            "result_id": result.id,
            "test_code": result.test_code,
            "test_name": getattr(result, "test_name", None),
            "value": result.value,
            "unit": result.unit,
            "lis_flags": result.lis_flags,
            "verification_status": result.verification_status.value,
            "verification_method": result.verification_method,
            "verified_at": result.verified_at.isoformat() if result.verified_at else None,
            "created_at": result.created_at.isoformat(),
            "updated_at": result.updated_at.isoformat(),
        }

    def get_pending_verification_queue(
        self, tenant_id: str, limit: int = 100
    ) -> list[dict]:
        """
        Get list of results pending verification.

        Args:
            tenant_id: Tenant identifier
            limit: Maximum number of results to return

        Returns:
            List of result summaries with verification status PENDING
        """
        logger.debug(f"Getting pending verification queue for tenant {tenant_id}")

        results, _ = self.result_repository.list_by_tenant(
            tenant_id=tenant_id,
            status=ResultStatus.PENDING,
            limit=limit,
        )

        return [
            {
                "result_id": r.id,
                "sample_id": r.sample_id,
                "test_code": r.test_code,
                "test_name": getattr(r, "test_name", None),
                "value": r.value,
                "unit": r.unit,
                "lis_flags": r.lis_flags,
                "created_at": r.created_at.isoformat(),
            }
            for r in results
        ]
