# LIS Integration Service

Laboratory Information System Integration Service for IVD Middleware.

**📋 Specification:** See [SPECIFICATION-LIS-INTEGRATION.md](../../SPECIFICATION-LIS-INTEGRATION.md) for detailed requirements, acceptance criteria, and business rules.

## Responsibility

- Connect to external LIS systems (push and pull models)
- Ingest samples and results
- Duplicate detection
- LIS adapter management (Mock, File Upload, REST API)

## Features

- Multiple LIS adapter implementations
- Push model: Receive orders via API endpoint
- Pull model: Background jobs to retrieve data from LIS
- Sample and result data normalization
- Tenant-specific LIS configurations

## API Endpoints

### LIS Configuration
- `POST /api/v1/lis/config` - Configure LIS connection
- `GET /api/v1/lis/config` - Get LIS configuration
- `GET /api/v1/lis/connection-status` - Test LIS connection

### Ingestion (Push Model)
- `POST /api/v1/lis/ingest` - Receive orders from external LIS

### File Upload
- `POST /api/v1/lis/manual-upload` - Upload CSV file

### Samples & Results
- `GET /api/v1/samples` - Query samples for tenant
- `GET /api/v1/samples/{id}` - Get sample details
- `GET /api/v1/samples/{id}/results` - Get results for sample

## LIS Adapters

- **MockLISAdapter**: Generates test data
- **FileUploadAdapter**: Processes CSV files
- **RESTAPIIncomingAdapter**: Receives push data from LIS
- **RESTAPIOutgoingAdapter**: Polls LIS APIs (pull model)

## Running

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn app.main:app --reload --port 8001

# Run with Celery worker (for pull model)
celery -A app.tasks.worker worker --loglevel=info

# Run tests
pytest
```

## Architecture

Follows Hexagonal Architecture with multi-tenant support.
