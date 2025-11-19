"""Verification settings API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

from app.services import SettingsService
from app.dependencies import get_settings_service, get_current_tenant_id, get_current_user
from app.exceptions import (
    SettingsNotFoundError,
    SettingsAlreadyExistsError,
    InvalidConfigurationError,
    InsufficientPermissionError,
)


# Request/Response Models
class AutoVerificationSettingsCreate(BaseModel):
    """Request model for creating auto-verification settings."""

    test_code: str = Field(..., description="Test code (e.g., 'GLU', 'WBC')")
    test_name: str = Field(..., description="Test name (e.g., 'Glucose', 'White Blood Count')")
    reference_range_low: Optional[float] = Field(None, description="Lower bound of reference range")
    reference_range_high: Optional[float] = Field(None, description="Upper bound of reference range")
    critical_range_low: Optional[float] = Field(None, description="Lower critical threshold")
    critical_range_high: Optional[float] = Field(None, description="Upper critical threshold")
    instrument_flags_to_block: Optional[List[str]] = Field(
        None,
        description="List of instrument flags that block auto-verification"
    )
    delta_check_threshold_percent: Optional[float] = Field(
        None,
        description="Maximum allowed percentage change from previous result"
    )
    delta_check_lookback_days: int = Field(30, description="Days to look back for previous result")

    class Config:
        json_schema_extra = {
            "example": {
                "test_code": "GLU",
                "test_name": "Glucose",
                "reference_range_low": 70.0,
                "reference_range_high": 100.0,
                "critical_range_low": 40.0,
                "critical_range_high": 400.0,
                "instrument_flags_to_block": ["H", "L", "C"],
                "delta_check_threshold_percent": 50.0,
                "delta_check_lookback_days": 30
            }
        }


class AutoVerificationSettingsUpdate(BaseModel):
    """Request model for updating auto-verification settings."""

    test_name: Optional[str] = Field(None, description="Test name")
    reference_range_low: Optional[float] = Field(None, description="Lower bound of reference range")
    reference_range_high: Optional[float] = Field(None, description="Upper bound of reference range")
    critical_range_low: Optional[float] = Field(None, description="Lower critical threshold")
    critical_range_high: Optional[float] = Field(None, description="Upper critical threshold")
    instrument_flags_to_block: Optional[List[str]] = Field(
        None,
        description="List of instrument flags that block auto-verification"
    )
    delta_check_threshold_percent: Optional[float] = Field(
        None,
        description="Maximum allowed percentage change from previous result"
    )
    delta_check_lookback_days: Optional[int] = Field(None, description="Days to look back for previous result")

    class Config:
        json_schema_extra = {
            "example": {
                "reference_range_low": 65.0,
                "reference_range_high": 110.0,
                "delta_check_threshold_percent": 40.0
            }
        }


class AutoVerificationSettingsResponse(BaseModel):
    """Response model for auto-verification settings."""

    id: str
    tenant_id: str
    test_code: str
    test_name: str
    reference_range_low: Optional[float]
    reference_range_high: Optional[float]
    critical_range_low: Optional[float]
    critical_range_high: Optional[float]
    instrument_flags_to_block: List[str]
    delta_check_threshold_percent: Optional[float]
    delta_check_lookback_days: int
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class SettingsListResponse(BaseModel):
    """Response model for list of settings."""

    settings: List[AutoVerificationSettingsResponse]
    total: int
    skip: int
    limit: int


# Router
verification_router = APIRouter(
    prefix="/api/v1/verification",
    tags=["verification"]
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


@verification_router.get(
    "",
    response_model=SettingsListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all verification settings",
    description="Retrieve all auto-verification settings for the tenant with pagination support."
)
async def list_verification_settings(
    settings_service: SettingsService = Depends(get_settings_service),
    tenant_id: str = Depends(get_current_tenant_id),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
):
    """
    List all auto-verification settings for the tenant.

    Returns settings for all configured test codes with pagination.
    Results are sorted by test code alphabetically.
    """
    try:
        result = settings_service.list_settings(
            tenant_id=tenant_id,
            skip=skip,
            limit=limit
        )

        # Convert settings to response models
        settings_responses = [
            AutoVerificationSettingsResponse(
                id=s["id"],
                tenant_id=tenant_id,
                test_code=s["test_code"],
                test_name=s["test_name"],
                reference_range_low=s["reference_range_low"],
                reference_range_high=s["reference_range_high"],
                critical_range_low=s["critical_range_low"],
                critical_range_high=s["critical_range_high"],
                instrument_flags_to_block=s["instrument_flags_to_block"],
                delta_check_threshold_percent=s["delta_check_threshold_percent"],
                delta_check_lookback_days=s["delta_check_lookback_days"],
                created_at=s["created_at"],
                updated_at=s["updated_at"],
            )
            for s in result["settings"]
        ]

        return SettingsListResponse(
            settings=settings_responses,
            total=result["total"],
            skip=result["skip"],
            limit=result["limit"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing verification settings: {str(e)}"
        )


@verification_router.get(
    "/{test_code}",
    response_model=AutoVerificationSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get verification settings for test",
    description="Retrieve auto-verification settings for a specific test code."
)
async def get_verification_settings(
    test_code: str,
    settings_service: SettingsService = Depends(get_settings_service),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """
    Get auto-verification settings for a specific test code.

    Args:
        test_code: Test code to retrieve settings for (e.g., "GLU", "WBC")

    Returns:
        Settings configuration for the specified test code

    Raises:
        404: If settings not found for this test code
    """
    try:
        settings = settings_service.get_settings(tenant_id, test_code)

        return AutoVerificationSettingsResponse(
            id=settings.id,
            tenant_id=settings.tenant_id,
            test_code=settings.test_code,
            test_name=settings.test_name,
            reference_range_low=settings.reference_range_low,
            reference_range_high=settings.reference_range_high,
            critical_range_low=settings.critical_range_low,
            critical_range_high=settings.critical_range_high,
            instrument_flags_to_block=settings.get_instrument_flags_to_block(),
            delta_check_threshold_percent=settings.delta_check_threshold_percent,
            delta_check_lookback_days=settings.delta_check_lookback_days,
            created_at=settings.created_at.isoformat(),
            updated_at=settings.updated_at.isoformat(),
        )

    except SettingsNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification settings not found for test code '{test_code}'"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving verification settings: {str(e)}"
        )


@verification_router.post(
    "",
    response_model=AutoVerificationSettingsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create verification settings",
    description="Create new auto-verification settings for a test code. Admin only."
)
async def create_verification_settings(
    settings_data: AutoVerificationSettingsCreate,
    settings_service: SettingsService = Depends(get_settings_service),
    tenant_id: str = Depends(get_current_tenant_id),
    user: dict = Depends(require_admin_role),
):
    """
    Create new auto-verification settings for a test code.

    Only users with admin role can create verification settings.
    Settings define the rules for automatic verification including reference ranges,
    critical ranges, blocked instrument flags, and delta check thresholds.

    Args:
        settings_data: Settings configuration to create

    Returns:
        Created settings record

    Raises:
        403: If user doesn't have admin role
        409: If settings already exist for this test code
        400: If configuration is invalid
    """
    try:
        settings = settings_service.create_settings(
            tenant_id=tenant_id,
            test_code=settings_data.test_code,
            test_name=settings_data.test_name,
            reference_range_low=settings_data.reference_range_low,
            reference_range_high=settings_data.reference_range_high,
            critical_range_low=settings_data.critical_range_low,
            critical_range_high=settings_data.critical_range_high,
            instrument_flags_to_block=settings_data.instrument_flags_to_block,
            delta_check_threshold_percent=settings_data.delta_check_threshold_percent,
            delta_check_lookback_days=settings_data.delta_check_lookback_days,
        )

        return AutoVerificationSettingsResponse(
            id=settings.id,
            tenant_id=settings.tenant_id,
            test_code=settings.test_code,
            test_name=settings.test_name,
            reference_range_low=settings.reference_range_low,
            reference_range_high=settings.reference_range_high,
            critical_range_low=settings.critical_range_low,
            critical_range_high=settings.critical_range_high,
            instrument_flags_to_block=settings.get_instrument_flags_to_block(),
            delta_check_threshold_percent=settings.delta_check_threshold_percent,
            delta_check_lookback_days=settings.delta_check_lookback_days,
            created_at=settings.created_at.isoformat(),
            updated_at=settings.updated_at.isoformat(),
        )

    except SettingsAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Verification settings already exist for test code '{settings_data.test_code}'"
        )
    except InvalidConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating verification settings: {str(e)}"
        )


@verification_router.put(
    "/{test_code}",
    response_model=AutoVerificationSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update verification settings",
    description="Update auto-verification settings for a test code. Admin only."
)
async def update_verification_settings(
    test_code: str,
    settings_data: AutoVerificationSettingsUpdate,
    settings_service: SettingsService = Depends(get_settings_service),
    tenant_id: str = Depends(get_current_tenant_id),
    user: dict = Depends(require_admin_role),
):
    """
    Update auto-verification settings for a test code.

    Only users with admin role can update verification settings.
    Only provided fields will be updated; omitted fields remain unchanged.

    Args:
        test_code: Test code to update settings for
        settings_data: Settings fields to update

    Returns:
        Updated settings record

    Raises:
        403: If user doesn't have admin role
        404: If settings not found for this test code
        400: If updated configuration is invalid
    """
    try:
        settings = settings_service.update_settings(
            tenant_id=tenant_id,
            test_code=test_code,
            test_name=settings_data.test_name,
            reference_range_low=settings_data.reference_range_low,
            reference_range_high=settings_data.reference_range_high,
            critical_range_low=settings_data.critical_range_low,
            critical_range_high=settings_data.critical_range_high,
            instrument_flags_to_block=settings_data.instrument_flags_to_block,
            delta_check_threshold_percent=settings_data.delta_check_threshold_percent,
            delta_check_lookback_days=settings_data.delta_check_lookback_days,
        )

        return AutoVerificationSettingsResponse(
            id=settings.id,
            tenant_id=settings.tenant_id,
            test_code=settings.test_code,
            test_name=settings.test_name,
            reference_range_low=settings.reference_range_low,
            reference_range_high=settings.reference_range_high,
            critical_range_low=settings.critical_range_low,
            critical_range_high=settings.critical_range_high,
            instrument_flags_to_block=settings.get_instrument_flags_to_block(),
            delta_check_threshold_percent=settings.delta_check_threshold_percent,
            delta_check_lookback_days=settings.delta_check_lookback_days,
            created_at=settings.created_at.isoformat(),
            updated_at=settings.updated_at.isoformat(),
        )

    except SettingsNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification settings not found for test code '{test_code}'"
        )
    except InvalidConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating verification settings: {str(e)}"
        )


@verification_router.delete(
    "/{test_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete verification settings",
    description="Delete auto-verification settings for a test code. Admin only."
)
async def delete_verification_settings(
    test_code: str,
    settings_service: SettingsService = Depends(get_settings_service),
    tenant_id: str = Depends(get_current_tenant_id),
    user: dict = Depends(require_admin_role),
):
    """
    Delete auto-verification settings for a test code.

    Only users with admin role can delete verification settings.
    This will remove all configuration for the specified test code.
    Results for this test code will no longer be auto-verified.

    Args:
        test_code: Test code to delete settings for

    Returns:
        204 No Content on success

    Raises:
        403: If user doesn't have admin role
        404: If settings not found for this test code
    """
    try:
        settings_service.delete_settings(tenant_id, test_code)
        return None

    except SettingsNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Verification settings not found for test code '{test_code}'"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting verification settings: {str(e)}"
        )
