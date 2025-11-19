"""Verification rules API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional

from app.services import SettingsService
from app.dependencies import get_settings_service, get_current_tenant_id, get_current_user
from app.exceptions import (
    RuleNotFoundError,
    InvalidConfigurationError,
    InsufficientPermissionError,
)


# Request/Response Models
class RuleEnablementRequest(BaseModel):
    """Request model for enabling/disabling a verification rule."""

    rule_type: str = Field(
        ...,
        description="Rule type to enable or disable"
    )
    enabled: bool = Field(
        ...,
        description="Whether to enable (true) or disable (false) the rule"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "rule_type": "delta_check",
                "enabled": True
            }
        }


class RuleResponse(BaseModel):
    """Response model for a verification rule."""

    id: str
    rule_type: str
    enabled: bool
    priority: int
    description: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class RulesListResponse(BaseModel):
    """Response model for list of verification rules."""

    rules: List[RuleResponse]
    total: int


# Router
rules_router = APIRouter(
    prefix="/api/v1/verification/rules",
    tags=["verification-rules"]
)


def require_admin_role(user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to ensure user has admin role.

    Args:
        user: Current authenticated user

    Returns:
        User dict if authorized

    Raises:
        HTTPException: If user doesn't have admin role
    """
    if user.get("role") not in ["admin", "administrator"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions. Admin role required."
        )
    return user


@rules_router.get(
    "",
    response_model=RulesListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all verification rules",
    description="Retrieve all verification rules for the tenant with their enabled status."
)
async def list_verification_rules(
    settings_service: SettingsService = Depends(get_settings_service),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    List all verification rules for the tenant.

    Returns all available verification rules with their current enabled/disabled status.
    Rules are ordered by priority (lower numbers execute first).

    Available rule types:
    - reference_range: Checks if value is within normal reference range
    - critical_range: Checks if value is within critical thresholds
    - instrument_flag: Checks for blocked instrument flags
    - delta_check: Checks for significant change from previous result

    Returns:
        List of verification rules with enabled status and descriptions
    """
    try:
        rules_data = settings_service.get_rules(tenant_id)

        rules_responses = [
            RuleResponse(
                id=rule["id"],
                rule_type=rule["rule_type"],
                enabled=rule["enabled"],
                priority=rule["priority"],
                description=rule["description"],
                created_at=rule["created_at"],
                updated_at=rule["updated_at"],
            )
            for rule in rules_data
        ]

        return RulesListResponse(
            rules=rules_responses,
            total=len(rules_responses)
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing verification rules: {str(e)}"
        )


@rules_router.put(
    "",
    response_model=RuleResponse,
    status_code=status.HTTP_200_OK,
    summary="Enable or disable verification rule",
    description="Enable or disable a specific verification rule type. Admin only."
)
async def update_rule_enablement(
    request: RuleEnablementRequest,
    settings_service: SettingsService = Depends(get_settings_service),
    tenant_id: str = Depends(get_current_tenant_id),
    user: dict = Depends(require_admin_role),
):
    """
    Enable or disable a specific verification rule type.

    Only users with admin role can modify rule enablement.
    Disabling a rule means it will be skipped during auto-verification,
    which may result in more results being auto-verified.

    Valid rule types:
    - reference_range: Value within normal range check
    - critical_range: Value within critical thresholds check
    - instrument_flag: Blocked instrument flag check
    - delta_check: Significant change from previous result check

    Args:
        request: Rule type and enabled status

    Returns:
        Updated rule configuration

    Raises:
        403: If user doesn't have admin role
        404: If rule type not found
        400: If rule type is invalid
    """
    try:
        if request.enabled:
            rule = settings_service.enable_rule(tenant_id, request.rule_type)
            action = "enabled"
        else:
            rule = settings_service.disable_rule(tenant_id, request.rule_type)
            action = "disabled"

        return RuleResponse(
            id=rule.id,
            rule_type=rule.rule_type.value,
            enabled=rule.enabled,
            priority=rule.priority,
            description=rule.description,
            created_at=rule.created_at.isoformat(),
            updated_at=rule.updated_at.isoformat(),
        )

    except RuleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification rule '{request.rule_type}' not found for tenant"
        )
    except InvalidConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating rule enablement: {str(e)}"
        )
