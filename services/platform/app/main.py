"""Main application entry point for Platform Service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import AppSettings
from app.api import tenants_router, users_router, auth_router


# Create FastAPI application
settings = AppSettings()

app = FastAPI(
    title="IVD Middleware - Platform Service",
    description="Identity & Multi-Tenancy Service",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix=settings.api_v1_prefix)
app.include_router(tenants_router, prefix=settings.api_v1_prefix)
app.include_router(users_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": settings.service_name,
        "environment": settings.environment
    }


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "IVD Middleware - Platform Service",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
