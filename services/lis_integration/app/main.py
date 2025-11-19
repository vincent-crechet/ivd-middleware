"""Main application entry point for LIS Integration Service."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import AppSettings
from app.api import samples_router, results_router, lis_config_router


# Create FastAPI application
settings = AppSettings()

app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version
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
app.include_router(samples_router, prefix=settings.api_v1_prefix)
app.include_router(results_router, prefix=settings.api_v1_prefix)
app.include_router(lis_config_router, prefix=settings.api_v1_prefix)


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
        "service": "IVD Middleware - LIS Integration Service",
        "version": "1.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.server_host, port=settings.server_port)
