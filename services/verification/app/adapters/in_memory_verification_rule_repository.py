"""In-memory implementation of verification rule repository for testing."""

import uuid
import copy

from app.ports import IVerificationRuleRepository
from app.models import VerificationRule
from app.exceptions import RuleNotFoundError


class InMemoryVerificationRuleRepository(IVerificationRuleRepository):
    """In-memory implementation of verification rule repository for testing."""

    def __init__(self):
        """Initialize with empty storage."""
        self._rules: dict[str, VerificationRule] = {}

    def get_by_tenant(self, tenant_id: str) -> list[VerificationRule]:
        """List all verification rules for a tenant, ordered by priority."""
        rules = [
            copy.deepcopy(r) for r in self._rules.values()
            if r.tenant_id == tenant_id
        ]
        # Sort by priority (ascending)
        rules.sort(key=lambda r: r.priority)
        return rules

    def update(self, rule: VerificationRule) -> VerificationRule:
        """Update an existing verification rule."""
        if not rule.id or rule.id not in self._rules:
            raise RuleNotFoundError(f"Rule with id '{rule.id}' not found")

        existing = self._rules[rule.id]
        if existing.tenant_id != rule.tenant_id:
            raise RuleNotFoundError(f"Rule with id '{rule.id}' not found")

        rule.update_timestamp()
        self._rules[rule.id] = copy.deepcopy(rule)
        return copy.deepcopy(rule)

    def list_all(
        self,
        tenant_id: str,
        enabled_only: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[VerificationRule], int]:
        """List all verification rules for a tenant with pagination."""
        # Filter by tenant
        rules = [
            r for r in self._rules.values()
            if r.tenant_id == tenant_id
        ]

        # Apply enabled filter
        if enabled_only:
            rules = [r for r in rules if r.enabled]

        # Sort by priority (ascending)
        rules.sort(key=lambda r: r.priority)

        total = len(rules)
        paginated = rules[skip:skip + limit]

        return [copy.deepcopy(r) for r in paginated], total

    # Helper methods for testing
    def create(self, rule: VerificationRule) -> VerificationRule:
        """
        Create a new verification rule (helper for testing).

        Note: This method is not part of the port interface but is useful
        for test setup and initialization.
        """
        if not rule.tenant_id:
            raise ValueError("Rule must have a tenant_id")

        # Generate ID if not provided
        if not rule.id:
            rule.id = str(uuid.uuid4())

        # Store copy to avoid external mutations
        self._rules[rule.id] = copy.deepcopy(rule)
        return copy.deepcopy(self._rules[rule.id])
