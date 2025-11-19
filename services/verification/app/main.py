"""Main application entry point for Verification Service."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import AppSettings
from app.dependencies import get_settings_service, get_settings
from app.exceptions import (
    VerificationException,
    SettingsNotFoundError,
    SettingsAlreadyExistsError,
    ReviewNotFoundError,
    ReviewAlreadyExistsError,
    ReviewCannotBeModifiedError,
    ReviewStateTransitionError,
    ResultNotFoundError,
    SampleNotFoundError,
    RuleNotFoundError,
    InvalidConfigurationError,
    InvalidReviewDecisionError,
    InvalidResultDecisionError,
    InsufficientPermissionError,
)

# Import routers from API modules
# These will be created in the app/api directory
try:
    from app.api.verification import router as verification_router
    from app.api.settings import router as settings_router
    from app.api.rules import router as rules_router
    from app.api.reviews import router as reviews_router
    HAS_API_ROUTERS = True
except ImportError:
    HAS_API_ROUTERS = False
    verification_router = None
    settings_router = None
    rules_router = None
    reviews_router = None


# Configure logging
def configure_logging(settings: AppSettings):
    """Configure application logging."""
    logging.basicConfig(
        level=settings.log_level,
        format=settings.log_format,
    )
    # Set log levels for specific loggers
    logging.getLogger("app").setLevel(settings.log_level)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


# Application lifespan events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown events for the application.
    """
    # Startup
    settings = get_settings()
    configure_logging(settings)
    logger = logging.getLogger(__name__)

    logger.info(f"Starting {settings.service_name}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Database: {'Real' if settings.use_real_database else 'In-Memory'}")

    # Initialize default verification rules for new tenants if enabled
    if settings.initialize_default_rules_on_startup:
        try:
            logger.info("Checking for default verification rules initialization")
            # Note: In production, this would be done through a proper migration
            # or tenant onboarding process, not on every startup
            # For now, we just log the intention
            logger.info("Default rules initialization would happen here")
        except Exception as e:
            logger.error(f"Failed to initialize default rules: {e}")

    logger.info(f"{settings.service_name} started successfully")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.service_name}")


# Create FastAPI application
settings = AppSettings()

app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    lifespan=lifespan
)


# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins if settings.environment != "production" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(SettingsNotFoundError)
async def settings_not_found_handler(request: Request, exc: SettingsNotFoundError):
    """Handle settings not found errors."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "settings_not_found",
            "message": str(exc),
            "detail": "The requested verification settings do not exist"
        }
    )


@app.exception_handler(SettingsAlreadyExistsError)
async def settings_already_exists_handler(request: Request, exc: SettingsAlreadyExistsError):
    """Handle settings already exist errors."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "settings_already_exist",
            "message": str(exc),
            "detail": "Verification settings already exist for this test code"
        }
    )


@app.exception_handler(ReviewNotFoundError)
async def review_not_found_handler(request: Request, exc: ReviewNotFoundError):
    """Handle review not found errors."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "review_not_found",
            "message": str(exc),
            "detail": "The requested review does not exist"
        }
    )


@app.exception_handler(ReviewAlreadyExistsError)
async def review_already_exists_handler(request: Request, exc: ReviewAlreadyExistsError):
    """Handle review already exists errors."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "review_already_exists",
            "message": str(exc),
            "detail": "A review already exists for this sample"
        }
    )


@app.exception_handler(ReviewCannotBeModifiedError)
async def review_cannot_be_modified_handler(request: Request, exc: ReviewCannotBeModifiedError):
    """Handle review modification errors."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "review_cannot_be_modified",
            "message": str(exc),
            "detail": "This review is already completed and cannot be modified"
        }
    )


@app.exception_handler(ReviewStateTransitionError)
async def review_state_transition_handler(request: Request, exc: ReviewStateTransitionError):
    """Handle invalid review state transition errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "invalid_state_transition",
            "message": str(exc),
            "detail": "The requested state transition is not allowed"
        }
    )


@app.exception_handler(ResultNotFoundError)
async def result_not_found_handler(request: Request, exc: ResultNotFoundError):
    """Handle result not found errors."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "result_not_found",
            "message": str(exc),
            "detail": "The requested result does not exist"
        }
    )


@app.exception_handler(SampleNotFoundError)
async def sample_not_found_handler(request: Request, exc: SampleNotFoundError):
    """Handle sample not found errors."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "sample_not_found",
            "message": str(exc),
            "detail": "The requested sample does not exist"
        }
    )


@app.exception_handler(RuleNotFoundError)
async def rule_not_found_handler(request: Request, exc: RuleNotFoundError):
    """Handle rule not found errors."""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "rule_not_found",
            "message": str(exc),
            "detail": "The requested verification rule does not exist"
        }
    )


@app.exception_handler(InvalidConfigurationError)
async def invalid_configuration_handler(request: Request, exc: InvalidConfigurationError):
    """Handle invalid configuration errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "invalid_configuration",
            "message": str(exc),
            "detail": "The provided configuration is invalid"
        }
    )


@app.exception_handler(InvalidReviewDecisionError)
async def invalid_review_decision_handler(request: Request, exc: InvalidReviewDecisionError):
    """Handle invalid review decision errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "invalid_review_decision",
            "message": str(exc),
            "detail": "The provided review decision is invalid"
        }
    )


@app.exception_handler(InvalidResultDecisionError)
async def invalid_result_decision_handler(request: Request, exc: InvalidResultDecisionError):
    """Handle invalid result decision errors."""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "invalid_result_decision",
            "message": str(exc),
            "detail": "The provided result decision is invalid"
        }
    )


@app.exception_handler(InsufficientPermissionError)
async def insufficient_permission_handler(request: Request, exc: InsufficientPermissionError):
    """Handle insufficient permission errors."""
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={
            "error": "insufficient_permission",
            "message": str(exc),
            "detail": "You do not have permission to perform this action"
        }
    )


@app.exception_handler(VerificationException)
async def verification_exception_handler(request: Request, exc: VerificationException):
    """Handle generic verification service exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "verification_error",
            "message": str(exc),
            "detail": "An error occurred in the verification service"
        }
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions."""
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "detail": str(exc) if settings.environment != "production" else None
        }
    )


# Include API routers
if HAS_API_ROUTERS:
    if verification_router:
        app.include_router(
            verification_router,
            prefix=f"{settings.api_v1_prefix}/verification",
            tags=["verification"]
        )

    if settings_router:
        app.include_router(
            settings_router,
            prefix=f"{settings.api_v1_prefix}/verification/settings",
            tags=["settings"]
        )

    if rules_router:
        app.include_router(
            rules_router,
            prefix=f"{settings.api_v1_prefix}/verification/rules",
            tags=["rules"]
        )

    if reviews_router:
        app.include_router(
            reviews_router,
            prefix=f"{settings.api_v1_prefix}/reviews",
            tags=["reviews"]
        )
else:
    logging.warning("API routers not found - application will have no endpoints")


# Health check endpoint
@app.get("/health")
def health_check():
    """
    Health check endpoint.

    Returns service status and basic information.
    Used by load balancers and monitoring systems.
    """
    return {
        "status": "healthy",
        "service": settings.service_name,
        "environment": settings.environment,
        "version": settings.api_version
    }


# Root endpoint
@app.get("/")
def root():
    """
    Root endpoint.

    Returns service information and links to documentation.
    """
    return {
        "service": "IVD Middleware - Verification Service",
        "description": "Automated verification and manual review of test results",
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/health",
        "features": {
            "auto_verification": settings.enable_auto_verification,
            "delta_check": settings.enable_delta_check,
            "review_escalation": settings.enable_review_escalation,
            "audit_trail": settings.enable_audit_trail
        }
    }


# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=settings.server_host,
        port=settings.server_port,
        log_level=settings.log_level.lower()
    )
