"""API Gateway for IVD Middleware."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx

app = FastAPI(
    title="IVD Middleware - API Gateway",
    description="Single entry point for all services",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs (from environment in production)
PLATFORM_SERVICE_URL = "http://platform:8000"
LIS_SERVICE_URL = "http://lis_integration:8001"
VERIFICATION_SERVICE_URL = "http://verification:8002"


@app.api_route("/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(service: str, path: str, request: Request):
    """
    Proxy requests to appropriate backend service.
    
    Routes:
    - /platform/* -> Platform Service
    - /lis/* -> LIS Integration Service
    - /verification/* -> Verification Service
    """
    # Determine target service
    service_urls = {
        "platform": PLATFORM_SERVICE_URL,
        "lis": LIS_SERVICE_URL,
        "verification": VERIFICATION_SERVICE_URL
    }
    
    target_url = service_urls.get(service)
    if not target_url:
        return JSONResponse(
            status_code=404,
            content={"detail": f"Service '{service}' not found"}
        )
    
    # Forward request
    url = f"{target_url}/{path}"
    headers = dict(request.headers)
    headers.pop("host", None)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=await request.body(),
                params=request.query_params
            )
            return JSONResponse(
                status_code=response.status_code,
                content=response.json() if response.headers.get("content-type") == "application/json" else response.text
            )
        except Exception as e:
            return JSONResponse(
                status_code=502,
                content={"detail": f"Error connecting to {service}: {str(e)}"}
            )


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "api-gateway"}


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "service": "IVD Middleware - API Gateway",
        "version": "1.0.0",
        "services": {
            "platform": "/platform/*",
            "lis": "/lis/*",
            "verification": "/verification/*"
        }
    }
