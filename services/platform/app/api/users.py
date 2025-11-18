"""User management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

from app.services import UserService
from app.dependencies import get_user_service, get_current_tenant_id
from app.models import UserRole
from app.exceptions import UserNotFoundError, DuplicateUserError, InvalidPasswordError


router = APIRouter(prefix="/users", tags=["users"])


# Request/Response Models
class UserCreate(BaseModel):
    """Request model for creating a user."""
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = UserRole.TECHNICIAN


class UserUpdate(BaseModel):
    """Request model for updating a user."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class PasswordChange(BaseModel):
    """Request model for changing password."""
    new_password: str = Field(..., min_length=8)


class UserResponse(BaseModel):
    """Response model for user data."""
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    tenant_id: str


# Endpoints
@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    user_service: UserService = Depends(get_user_service)
):
    """
    Create a new user in the authenticated tenant.

    Tenant ID is extracted from JWT token.
    """
    try:
        user = user_service.create_user(
            tenant_id=tenant_id,
            email=user_data.email,
            password=user_data.password,
            name=user_data.name,
            role=user_data.role
        )
        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role.value,
            is_active=user.is_active,
            tenant_id=user.tenant_id
        )
    except DuplicateUserError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except InvalidPasswordError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    user_service: UserService = Depends(get_user_service)
):
    """Get a user by ID within the authenticated tenant."""
    try:
        user = user_service.get_user(user_id, tenant_id)
        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role.value,
            is_active=user.is_active,
            tenant_id=user.tenant_id
        )
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/", response_model=list[UserResponse])
def list_users(
    page: int = 1,
    page_size: int = 20,
    tenant_id: str = Depends(get_current_tenant_id),
    user_service: UserService = Depends(get_user_service)
):
    """List users in the authenticated tenant with pagination."""
    users = user_service.list_users(tenant_id, page=page, page_size=page_size)
    return [
        UserResponse(
            id=u.id,
            email=u.email,
            name=u.name,
            role=u.role.value,
            is_active=u.is_active,
            tenant_id=u.tenant_id
        )
        for u in users
    ]


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    user_data: UserUpdate,
    tenant_id: str = Depends(get_current_tenant_id),
    user_service: UserService = Depends(get_user_service)
):
    """Update user information within the authenticated tenant."""
    try:
        user = user_service.update_user(
            user_id=user_id,
            tenant_id=tenant_id,
            name=user_data.name,
            role=user_data.role,
            is_active=user_data.is_active
        )
        return UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            role=user.role.value,
            is_active=user.is_active,
            tenant_id=user.tenant_id
        )
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    user_id: str,
    password_data: PasswordChange,
    tenant_id: str = Depends(get_current_tenant_id),
    user_service: UserService = Depends(get_user_service)
):
    """Change user password."""
    try:
        user_service.change_password(
            user_id=user_id,
            tenant_id=tenant_id,
            new_password=password_data.new_password
        )
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidPasswordError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: str,
    tenant_id: str = Depends(get_current_tenant_id),
    user_service: UserService = Depends(get_user_service)
):
    """Delete a user from the authenticated tenant."""
    try:
        user_service.delete_user(user_id, tenant_id)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
