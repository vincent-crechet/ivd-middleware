"""Verification rule repository port."""

import abc
from typing import Optional
from app.models import VerificationRule


class IVerificationRuleRepository(abc.ABC):
    """
    Port: Abstract contract for verification rule data persistence with multi-tenant support.

    All queries automatically filter by tenant_id to ensure data isolation.
    Rules define which verification checks are enabled and their priority order for a tenant.
    """

    @abc.abstractmethod
    def get_by_tenant(self, tenant_id: str) -> list[VerificationRule]:
        """
        List all verification rules for a tenant, ordered by priority.

        Args:
            tenant_id: Tenant identifier

        Returns:
            List of all rules for the tenant, sorted by priority (ascending)
        """
        pass

    @abc.abstractmethod
    def update(self, rule: VerificationRule) -> VerificationRule:
        """
        Update an existing verification rule.

        Args:
            rule: Rule with updated fields (must have ID)

        Returns:
            Updated rule

        Raises:
            RuleNotFoundError: If rule doesn't exist
        """
        pass

    @abc.abstractmethod
    def list_all(
        self,
        tenant_id: str,
        enabled_only: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[VerificationRule], int]:
        """
        List all verification rules for a tenant with pagination.

        Args:
            tenant_id: Tenant identifier
            enabled_only: If True, only return enabled rules
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of rules ordered by priority, total count)
        """
        pass
