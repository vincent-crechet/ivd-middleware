"""PostgreSQL implementation of verification rule repository."""

from sqlmodel import Session, select
import uuid

from app.ports import IVerificationRuleRepository
from app.models import VerificationRule
from app.exceptions import RuleNotFoundError


class PostgresVerificationRuleRepository(IVerificationRuleRepository):
    """PostgreSQL implementation of verification rule repository with multi-tenant support."""

    def __init__(self, session: Session):
        """
        Initialize with database session.

        Args:
            session: SQLModel database session
        """
        self._session = session

    def get_by_tenant(self, tenant_id: str) -> list[VerificationRule]:
        """List all verification rules for a tenant, ordered by priority."""
        statement = select(VerificationRule).where(
            VerificationRule.tenant_id == tenant_id
        ).order_by(VerificationRule.priority)

        return list(self._session.exec(statement).all())

    def update(self, rule: VerificationRule) -> VerificationRule:
        """Update an existing verification rule."""
        with self._session.no_autoflush:
            # Verify rule exists and belongs to tenant
            existing = self._session.exec(
                select(VerificationRule).where(
                    VerificationRule.id == rule.id,
                    VerificationRule.tenant_id == rule.tenant_id
                )
            ).first()

            if not existing:
                raise RuleNotFoundError(f"Rule with id '{rule.id}' not found")

            # Update fields
            existing.rule_type = rule.rule_type
            existing.enabled = rule.enabled
            existing.priority = rule.priority
            existing.description = rule.description
            existing.update_timestamp()

        self._session.add(existing)
        self._session.commit()
        self._session.refresh(existing)
        return existing

    def list_all(
        self,
        tenant_id: str,
        enabled_only: bool = False,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list[VerificationRule], int]:
        """List all verification rules for a tenant with pagination."""
        # Build base query
        query = select(VerificationRule).where(
            VerificationRule.tenant_id == tenant_id
        )

        # Apply enabled filter
        if enabled_only:
            query = query.where(VerificationRule.enabled == True)

        # Get total count before pagination
        count_query = select(VerificationRule).where(
            VerificationRule.tenant_id == tenant_id
        )
        if enabled_only:
            count_query = count_query.where(VerificationRule.enabled == True)

        total = len(self._session.exec(count_query).all())

        # Sort by priority (ascending) and apply pagination
        query = query.order_by(VerificationRule.priority).offset(skip).limit(limit)
        rules = list(self._session.exec(query).all())

        return rules, total

    # Helper method for initialization
    def create(self, rule: VerificationRule) -> VerificationRule:
        """
        Create a new verification rule (helper for initialization).

        Note: This method is not part of the port interface but is useful
        for system initialization and setup.
        """
        if not rule.tenant_id:
            raise ValueError("Rule must have a tenant_id")

        # Generate ID if not provided
        if not rule.id:
            rule.id = str(uuid.uuid4())

        self._session.add(rule)
        self._session.commit()
        self._session.refresh(rule)
        return rule
