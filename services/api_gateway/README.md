# API Gateway

Single entry point for all IVD Middleware services.

## Purpose

- Routes requests to appropriate backend services
- Handles CORS
- Can add authentication/rate limiting in future

## Routes

- `/platform/*` -> Platform Service (port 8000)
- `/lis/*` -> LIS Integration Service (port 8001)
- `/verification/*` -> Verification Service (port 8002)

## Running

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

Access services via: `http://localhost:8080/{service}/{path}`
