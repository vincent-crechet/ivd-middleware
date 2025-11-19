"""Verification Service repository adapter implementations."""

from .in_memory_auto_verification_settings_repository import InMemoryAutoVerificationSettingsRepository
from .in_memory_review_repository import InMemoryReviewRepository
from .in_memory_result_decision_repository import InMemoryResultDecisionRepository
from .in_memory_verification_rule_repository import InMemoryVerificationRuleRepository
from .postgres_auto_verification_settings_repository import PostgresAutoVerificationSettingsRepository
from .postgres_review_repository import PostgresReviewRepository
from .postgres_result_decision_repository import PostgresResultDecisionRepository
from .postgres_verification_rule_repository import PostgresVerificationRuleRepository

__all__ = [
    # In-memory adapters
    "InMemoryAutoVerificationSettingsRepository",
    "InMemoryReviewRepository",
    "InMemoryResultDecisionRepository",
    "InMemoryVerificationRuleRepository",
    # PostgreSQL adapters
    "PostgresAutoVerificationSettingsRepository",
    "PostgresReviewRepository",
    "PostgresResultDecisionRepository",
    "PostgresVerificationRuleRepository",
]
