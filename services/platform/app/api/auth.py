"""Authentication API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.services import AuthService
from app.dependencies import get_auth_service, get_current_user
from app.exceptions import InvalidCredentialsError


router = APIRouter(prefix="/auth", tags=["authentication"])


# Request/Response Models
class LoginRequest(BaseModel):
    """Request model for user login."""
    email: EmailStr
    password: str
    tenant_id: str


class LoginResponse(BaseModel):
    """Response model for successful login."""
    access_token: str
    token_type: str
    user: dict


class UserInfoResponse(BaseModel):
    """Response model for user information."""
    id: str
    email: str
    name: str
    role: str
    tenant_id: str


# Endpoints
@router.post("/login", response_model=LoginResponse)
def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Authenticate user and return access token.

    The token includes tenant_id and role for authorization.
    """
    try:
        result = auth_service.login(
            email=request.email,
            password=request.password,
            tenant_id=request.tenant_id
        )
        return result
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.get("/me", response_model=UserInfoResponse)
def get_current_user_info(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current authenticated user information.

    Requires valid JWT token.
    """
    return current_user
