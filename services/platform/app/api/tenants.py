"""Tenant management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from app.services import TenantService, TenantAdminService
from app.dependencies import get_tenant_service, get_tenant_admin_service
from app.exceptions import TenantNotFoundError, DuplicateTenantError, InvalidPasswordError


router = APIRouter(prefix="/tenants", tags=["tenants"])


# Request/Response Models
class TenantCreate(BaseModel):
    """Request model for creating a tenant."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)


class TenantWithAdminCreate(BaseModel):
    """Request model for creating tenant with first admin user (SPEC Feature 1)."""
    tenant_name: str = Field(..., min_length=1, max_length=255)
    tenant_description: Optional[str] = Field(None, max_length=2000)
    admin_name: str = Field(..., min_length=1, max_length=255)
    admin_email: str = Field(..., min_length=3, max_length=255)
    admin_password: str = Field(..., min_length=8)


class TenantUpdate(BaseModel):
    """Request model for updating a tenant."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    is_active: Optional[bool] = None


class TenantResponse(BaseModel):
    """Response model for tenant data."""
    id: str
    name: str
    description: Optional[str]
    is_active: bool


# Endpoints
@router.post("/with-admin", status_code=status.HTTP_201_CREATED)
def create_tenant_with_admin(
    request: TenantWithAdminCreate,
    service: TenantAdminService = Depends(get_tenant_admin_service)
):
    """
    Create a new tenant with first admin user (Primary onboarding endpoint).

    Per SPECIFICATION.md Feature 1:
    "During tenant creation, first admin user is created with name, email, and password"

    This is the recommended way to create new laboratory tenants.

    Returns:
        Dictionary with tenant and admin_user information
    """
    try:
        result = service.create_tenant_with_admin(
            tenant_name=request.tenant_name,
            tenant_description=request.tenant_description,
            admin_name=request.admin_name,
            admin_email=request.admin_email,
            admin_password=request.admin_password
        )
        return result
    except DuplicateTenantError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except InvalidPasswordError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
def create_tenant(
    tenant_data: TenantCreate,
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """
    Create a new tenant (without user - for system admin use).

    NOTE: For onboarding new laboratories, use POST /tenants/with-admin instead.

    Returns the created tenant immediately.
    """
    try:
        tenant = tenant_service.create_tenant(
            name=tenant_data.name,
            description=tenant_data.description
        )
        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            description=tenant.description,
            is_active=tenant.is_active
        )
    except DuplicateTenantError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: str,
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """Get a tenant by ID."""
    try:
        tenant = tenant_service.get_tenant(tenant_id)
        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            description=tenant.description,
            is_active=tenant.is_active
        )
    except TenantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/", response_model=list[TenantResponse])
def list_tenants(
    page: int = 1,
    page_size: int = 20,
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """List tenants with pagination."""
    tenants = tenant_service.list_tenants(page=page, page_size=page_size)
    return [
        TenantResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            is_active=t.is_active
        )
        for t in tenants
    ]


@router.put("/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: str,
    tenant_data: TenantUpdate,
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """Update tenant information."""
    try:
        tenant = tenant_service.update_tenant(
            tenant_id=tenant_id,
            name=tenant_data.name,
            description=tenant_data.description,
            is_active=tenant_data.is_active
        )
        return TenantResponse(
            id=tenant.id,
            name=tenant.name,
            description=tenant.description,
            is_active=tenant.is_active
        )
    except TenantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(
    tenant_id: str,
    tenant_service: TenantService = Depends(get_tenant_service)
):
    """Delete a tenant and all associated data."""
    try:
        tenant_service.delete_tenant(tenant_id)
    except TenantNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
