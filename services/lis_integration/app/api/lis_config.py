"""LIS Configuration API routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional

from app.services import LISConfigService
from app.models import LISType, IntegrationModel
from app.dependencies import get_lis_config_service, get_current_tenant_id
from app.exceptions import LISConfigNotFoundError, LISConfigurationError

lis_config_router = APIRouter(prefix="/lis", tags=["lis-config"])


# Request/Response models
class ConfigureRequest(BaseModel):
    """Request to configure LIS connection."""
    lis_type: LISType
    integration_model: IntegrationModel
    api_endpoint_url: Optional[str] = None
    api_auth_credentials: Optional[str] = None
    pull_interval_minutes: int = 5


class UpdateUploadSettingsRequest(BaseModel):
    """Request to update upload settings."""
    auto_upload_enabled: bool
    upload_verified_results: bool = True
    upload_rejected_results: bool = False
    upload_batch_size: int = 100
    upload_rate_limit: int = 100


class ConfigResponse(BaseModel):
    """LIS configuration response."""
    id: str
    tenant_id: str
    lis_type: str
    integration_model: str
    api_endpoint_url: Optional[str]
    pull_interval_minutes: int
    auto_upload_enabled: bool
    upload_verified_results: bool
    upload_rejected_results: bool
    upload_batch_size: int
    upload_rate_limit: int


@lis_config_router.post("/config")
async def configure_lis(
    request: ConfigureRequest,
    lis_config_service: LISConfigService = Depends(get_lis_config_service),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Configure LIS connection for tenant."""
    try:
        config = lis_config_service.create_configuration(
            tenant_id=tenant_id,
            lis_type=request.lis_type,
            integration_model=request.integration_model,
            api_endpoint_url=request.api_endpoint_url,
            api_auth_credentials=request.api_auth_credentials,
            pull_interval_minutes=request.pull_interval_minutes
        )

        return ConfigResponse(
            id=config.id,
            tenant_id=config.tenant_id,
            lis_type=config.lis_type.value,
            integration_model=config.integration_model.value,
            api_endpoint_url=config.api_endpoint_url,
            pull_interval_minutes=config.pull_interval_minutes,
            auto_upload_enabled=config.auto_upload_enabled,
            upload_verified_results=config.upload_verified_results,
            upload_rejected_results=config.upload_rejected_results,
            upload_batch_size=config.upload_batch_size,
            upload_rate_limit=config.upload_rate_limit,
        )
    except LISConfigurationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error configuring LIS: {str(e)}"
        )


@lis_config_router.get("/config")
async def get_config(
    lis_config_service: LISConfigService = Depends(get_lis_config_service),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Get LIS configuration for tenant."""
    try:
        config = lis_config_service.get_configuration(tenant_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="LIS not configured for this tenant"
            )

        return ConfigResponse(
            id=config.id,
            tenant_id=config.tenant_id,
            lis_type=config.lis_type.value,
            integration_model=config.integration_model.value,
            api_endpoint_url=config.api_endpoint_url,
            pull_interval_minutes=config.pull_interval_minutes,
            auto_upload_enabled=config.auto_upload_enabled,
            upload_verified_results=config.upload_verified_results,
            upload_rejected_results=config.upload_rejected_results,
            upload_batch_size=config.upload_batch_size,
            upload_rate_limit=config.upload_rate_limit,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving LIS configuration: {str(e)}"
        )


@lis_config_router.post("/connection-status")
async def test_connection(
    lis_config_service: LISConfigService = Depends(get_lis_config_service),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Test LIS connection health."""
    try:
        status_info = lis_config_service.test_connection(tenant_id)

        return {
            "is_connected": status_info["is_connected"],
            "last_tested_at": status_info["last_tested_at"].isoformat(),
            "error_message": status_info["error_message"],
            "details": status_info["details"],
        }
    except LISConfigNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LIS not configured for this tenant"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error testing LIS connection: {str(e)}"
        )


@lis_config_router.put("/config/upload-settings")
async def update_upload_settings(
    request: UpdateUploadSettingsRequest,
    lis_config_service: LISConfigService = Depends(get_lis_config_service),
    tenant_id: str = Depends(get_current_tenant_id),
):
    """Update LIS upload settings."""
    try:
        config = lis_config_service.update_upload_settings(
            tenant_id=tenant_id,
            auto_upload_enabled=request.auto_upload_enabled,
            upload_verified_results=request.upload_verified_results,
            upload_rejected_results=request.upload_rejected_results,
            upload_batch_size=request.upload_batch_size,
            upload_rate_limit=request.upload_rate_limit,
        )

        return ConfigResponse(
            id=config.id,
            tenant_id=config.tenant_id,
            lis_type=config.lis_type.value,
            integration_model=config.integration_model.value,
            api_endpoint_url=config.api_endpoint_url,
            pull_interval_minutes=config.pull_interval_minutes,
            auto_upload_enabled=config.auto_upload_enabled,
            upload_verified_results=config.upload_verified_results,
            upload_rejected_results=config.upload_rejected_results,
            upload_batch_size=config.upload_batch_size,
            upload_rate_limit=config.upload_rate_limit,
        )
    except LISConfigNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LIS not configured for this tenant"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating upload settings: {str(e)}"
        )
