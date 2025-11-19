"""Shared tests for VerificationRule repository implementations.

Tests both in-memory and PostgreSQL adapters using parametrized fixtures.
"""

import pytest
import uuid
from app.models import VerificationRule, RuleType
from app.ports import IVerificationRuleRepository

TEST_TENANT_ID = "test-tenant-123"


class TestVerificationRuleRepository:
    """Contract tests for IVerificationRuleRepository."""

    def test_create_rule(self, verification_rule_repository):
        """Test creating a new verification rule."""
        repo = verification_rule_repository
        rule = VerificationRule(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            rule_type=RuleType.REFERENCE_RANGE,
            enabled=True,
            priority=1,
            description="Check if value is within reference range",
        )

        created = repo.create(rule)

        assert created.id == rule.id
        assert created.tenant_id == TEST_TENANT_ID
        assert created.rule_type == RuleType.REFERENCE_RANGE
        assert created.enabled is True

    def test_get_by_tenant(self, verification_rule_repository):
        """Test retrieving all rules for a tenant, ordered by priority."""
        repo = verification_rule_repository

        # Create multiple rules with different priorities
        rule1 = VerificationRule(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            rule_type=RuleType.REFERENCE_RANGE,
            enabled=True,
            priority=3,
            description="Reference Range Check",
        )
        rule2 = VerificationRule(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            rule_type=RuleType.CRITICAL_RANGE,
            enabled=True,
            priority=1,
            description="Critical Range Check",
        )
        rule3 = VerificationRule(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            rule_type=RuleType.INSTRUMENT_FLAG,
            enabled=False,
            priority=2,
            description="Instrument Flag Check",
        )

        repo.create(rule1)
        repo.create(rule2)
        repo.create(rule3)

        # Get all rules for tenant - should be ordered by priority
        rules = repo.get_by_tenant(TEST_TENANT_ID)

        assert len(rules) == 3
        rule_types = {r.rule_type for r in rules}
        assert rule_types == {
            RuleType.REFERENCE_RANGE,
            RuleType.CRITICAL_RANGE,
            RuleType.INSTRUMENT_FLAG,
        }
        # Verify priority ordering
        priorities = [r.priority for r in rules]
        assert priorities == sorted(priorities)

    def test_update_rule_enabled_status(self, verification_rule_repository):
        """Test enabling/disabling a rule."""
        repo = verification_rule_repository

        rule = VerificationRule(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            rule_type=RuleType.REFERENCE_RANGE,
            enabled=True,
            priority=1,
            description="Reference Range",
        )
        created = repo.create(rule)

        # Disable the rule
        created.enabled = False
        updated = repo.update(created)

        assert updated.enabled is False

        # Re-enable the rule
        updated.enabled = True
        updated_again = repo.update(updated)

        assert updated_again.enabled is True

    def test_rule_priority_ordering(self, verification_rule_repository):
        """Test that rules are ordered by priority."""
        repo = verification_rule_repository

        # Create rules with different priorities
        rule1 = VerificationRule(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            rule_type=RuleType.REFERENCE_RANGE,
            enabled=True,
            priority=3,
            description="Reference Range",
        )
        rule2 = VerificationRule(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            rule_type=RuleType.CRITICAL_RANGE,
            enabled=True,
            priority=1,
            description="Critical Range",
        )
        rule3 = VerificationRule(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            rule_type=RuleType.INSTRUMENT_FLAG,
            enabled=True,
            priority=2,
            description="Instrument Flag",
        )

        repo.create(rule1)
        repo.create(rule2)
        repo.create(rule3)

        rules = repo.get_by_tenant(TEST_TENANT_ID)

        # Should be ordered by priority
        priorities = [r.priority for r in rules]
        assert priorities == sorted(priorities)

    def test_list_all_with_enabled_only_filter(self, verification_rule_repository):
        """Test listing rules with enabled_only filter."""
        repo = verification_rule_repository

        # Create enabled and disabled rules
        enabled_rule = VerificationRule(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            rule_type=RuleType.REFERENCE_RANGE,
            enabled=True,
            priority=1,
            description="Enabled",
        )
        disabled_rule = VerificationRule(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            rule_type=RuleType.CRITICAL_RANGE,
            enabled=False,
            priority=2,
            description="Disabled",
        )

        repo.create(enabled_rule)
        repo.create(disabled_rule)

        # Get all rules
        all_rules, count = repo.list_all(TEST_TENANT_ID, enabled_only=False)
        assert len(all_rules) == 2
        assert count == 2

        # Get only enabled rules
        enabled_rules, count = repo.list_all(TEST_TENANT_ID, enabled_only=True)
        assert len(enabled_rules) == 1
        assert count == 1
        assert enabled_rules[0].enabled is True
        assert enabled_rules[0].rule_type == RuleType.REFERENCE_RANGE

    def test_list_all_pagination(self, verification_rule_repository):
        """Test pagination when listing all rules."""
        repo = verification_rule_repository

        # Create 5 rules
        for i in range(5):
            rule = VerificationRule(
                id=str(uuid.uuid4()),
                tenant_id=TEST_TENANT_ID,
                rule_type=RuleType.REFERENCE_RANGE if i == 0 else RuleType.DELTA_CHECK,
                enabled=True,
                priority=i + 1,
                description=f"Rule {i}",
            )
            repo.create(rule)

        # Get first page (2 items)
        page1, count1 = repo.list_all(TEST_TENANT_ID, skip=0, limit=2)
        assert len(page1) == 2
        assert count1 == 5

        # Get second page
        page2, count2 = repo.list_all(TEST_TENANT_ID, skip=2, limit=2)
        assert len(page2) == 2
        assert count2 == 5

        # Get third page (1 item)
        page3, count3 = repo.list_all(TEST_TENANT_ID, skip=4, limit=2)
        assert len(page3) == 1
        assert count3 == 5

    def test_tenant_isolation(self, verification_rule_repository):
        """Test that rules are isolated per tenant."""
        repo = verification_rule_repository
        tenant1 = "tenant-1"
        tenant2 = "tenant-2"

        # Create rules for different tenants
        rule1 = VerificationRule(
            id=str(uuid.uuid4()),
            tenant_id=tenant1,
            rule_type=RuleType.REFERENCE_RANGE,
            enabled=True,
            priority=1,
            description="Tenant 1 rule",
        )
        rule2 = VerificationRule(
            id=str(uuid.uuid4()),
            tenant_id=tenant2,
            rule_type=RuleType.CRITICAL_RANGE,
            enabled=True,
            priority=1,
            description="Tenant 2 rule",
        )

        repo.create(rule1)
        repo.create(rule2)

        # List for tenant1 should only return tenant1 rules
        tenant1_rules = repo.get_by_tenant(tenant1)
        assert len(tenant1_rules) == 1
        assert tenant1_rules[0].tenant_id == tenant1

        # List for tenant2 should only return tenant2 rules
        tenant2_rules = repo.get_by_tenant(tenant2)
        assert len(tenant2_rules) == 1
        assert tenant2_rules[0].tenant_id == tenant2

    def test_all_rule_types(self, verification_rule_repository):
        """Test creating rules for all rule types."""
        repo = verification_rule_repository

        rule_types = [
            RuleType.REFERENCE_RANGE,
            RuleType.CRITICAL_RANGE,
            RuleType.INSTRUMENT_FLAG,
            RuleType.DELTA_CHECK,
        ]

        for i, rule_type in enumerate(rule_types):
            rule = VerificationRule(
                id=str(uuid.uuid4()),
                tenant_id=TEST_TENANT_ID,
                rule_type=rule_type,
                enabled=i % 2 == 0,  # Alternate enabled/disabled
                priority=i + 1,
                description=f"{rule_type.value} rule",
            )
            repo.create(rule)

        # Verify all were created
        rules = repo.get_by_tenant(TEST_TENANT_ID)
        assert len(rules) == 4

        created_types = {r.rule_type for r in rules}
        assert created_types == set(rule_types)

    def test_update_rule_priority(self, verification_rule_repository):
        """Test updating rule priority."""
        repo = verification_rule_repository

        rule = VerificationRule(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            rule_type=RuleType.REFERENCE_RANGE,
            enabled=True,
            priority=1,
            description="Initial priority",
        )
        created = repo.create(rule)

        # Update priority
        created.priority = 5
        updated = repo.update(created)

        assert updated.priority == 5

    def test_update_rule_description(self, verification_rule_repository):
        """Test updating rule description."""
        repo = verification_rule_repository

        rule = VerificationRule(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            rule_type=RuleType.CRITICAL_RANGE,
            enabled=True,
            priority=2,
            description="Original description",
        )
        created = repo.create(rule)

        # Update description
        created.description = "Updated description"
        updated = repo.update(created)

        assert updated.description == "Updated description"

    def test_get_active_rules_for_verification(self, verification_rule_repository):
        """Test retrieving enabled rules ordered by priority for verification."""
        repo = verification_rule_repository

        # Create rules with mixed enabled/disabled
        rule1 = VerificationRule(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            rule_type=RuleType.REFERENCE_RANGE,
            enabled=True,
            priority=3,
            description="Reference Range",
        )
        rule2 = VerificationRule(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            rule_type=RuleType.CRITICAL_RANGE,
            enabled=False,
            priority=1,
            description="Critical Range",
        )
        rule3 = VerificationRule(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            rule_type=RuleType.INSTRUMENT_FLAG,
            enabled=True,
            priority=2,
            description="Instrument Flag",
        )

        repo.create(rule1)
        repo.create(rule2)
        repo.create(rule3)

        # Get active (enabled) rules ordered by priority
        active_rules, count = repo.list_all(TEST_TENANT_ID, enabled_only=True)

        assert len(active_rules) == 2
        assert count == 2
        # Should be ordered by priority
        assert active_rules[0].priority == 2  # INSTRUMENT_FLAG
        assert active_rules[1].priority == 3  # REFERENCE_RANGE
        assert all(r.enabled for r in active_rules)

    def test_mixed_enabled_disabled_rules(self, verification_rule_repository):
        """Test repository with mix of enabled and disabled rules."""
        repo = verification_rule_repository

        # Create mixed set of rules
        for i in range(4):
            rule = VerificationRule(
                id=str(uuid.uuid4()),
                tenant_id=TEST_TENANT_ID,
                rule_type=RuleType.REFERENCE_RANGE if i == 0 else RuleType.DELTA_CHECK,
                enabled=i % 2 == 0,  # Alternate
                priority=i + 1,
                description=f"Rule {i}",
            )
            repo.create(rule)

        # Get all
        all_rules, all_count = repo.list_all(TEST_TENANT_ID, enabled_only=False)
        assert len(all_rules) == 4
        assert all_count == 4

        # Get enabled only
        enabled_rules, enabled_count = repo.list_all(TEST_TENANT_ID, enabled_only=True)
        assert len(enabled_rules) == 2
        assert enabled_count == 2
        assert all(r.enabled for r in enabled_rules)
