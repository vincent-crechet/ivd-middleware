# Verification & Review Service

The Verification & Review Service implements automated result verification and manual review workflows for the IVD Middleware. It applies configurable verification rules to laboratory results and routes exceptions to qualified staff for review.

## Architecture

Built on **Hexagonal Architecture** with:
- **Ports:** Abstract interfaces for repositories and external services
- **Adapters:** Concrete implementations (PostgreSQL + In-Memory for testing)
- **Services:** Business logic layer with dependency injection
- **API:** RESTful endpoints for configuration and workflows

## Key Components

### Verification Engine
- **Reference Range Check:** Validates result values within normal ranges
- **Critical Range Check:** Identifies critical/abnormal values
- **Instrument Flag Check:** Prevents auto-verify for results with blocking flags
- **Delta Check:** Detects significant changes from patient history

### Review Workflow
- Sample-level reviews (covering all flagged results)
- Manual approval/rejection with comments
- Escalation to pathologists for complex cases
- Complete audit trail of all decisions

### Settings Management
- Configure verification rules per test code
- Define reference ranges, critical ranges, instrument flags
- Delta check thresholds with lookback period
- Multi-tenant configuration isolation

## Directory Structure

```
app/
├── models/              # Domain models (AutoVerificationSettings, Review, etc.)
├── ports/               # Abstract interfaces (repositories, verification engine)
├── adapters/            # Concrete implementations (PostgreSQL, in-memory)
├── services/            # Business logic (VerificationService, ReviewService, etc.)
├── api/                 # API endpoints (verification, rules, reviews)
├── exceptions/          # Domain-specific exceptions
├── config.py            # Configuration management
├── dependencies.py      # Dependency injection setup
└── main.py              # FastAPI application

tests/
├── shared/              # Repository contract tests (both adapters)
├── unit/                # Service layer tests
└── integration/         # PostgreSQL-specific tests
```

## Development

### Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << 'ENVEOF'
DATABASE_URL=postgresql://localhost/verification
JWT_SECRET=your-secret-key
VERIFICATION_USE_REAL_DATABASE=true
ENVEOF
```

### Database

```bash
# Create PostgreSQL database
createdb verification

# Run migrations (if using alembic)
alembic upgrade head
```

### Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run only shared tests
pytest tests/shared/

# Run only unit tests
pytest tests/unit/

# Run with both in-memory and PostgreSQL adapters
pytest tests/ -v
```

### Run Service

```bash
# Development
uvicorn app.main:app --host 0.0.0.0 --port 8002 --reload

# Production (with 4 workers)
uvicorn app.main:app --host 0.0.0.0 --port 8002 --workers 4
```

## API Endpoints

### Settings Management
- `GET /api/v1/verification/settings` - List all settings
- `GET /api/v1/verification/settings/{test_code}` - Get specific test settings
- `POST /api/v1/verification/settings` - Create settings (admin)
- `PUT /api/v1/verification/settings/{test_code}` - Update settings (admin)
- `DELETE /api/v1/verification/settings/{test_code}` - Delete settings (admin)

### Rules Configuration
- `GET /api/v1/verification/rules` - List rule statuses
- `PUT /api/v1/verification/rules` - Enable/disable rules (admin)

### Review Workflow
- `GET /api/v1/reviews/queue` - Get review queue
- `GET /api/v1/reviews/{review_id}` - Get review details
- `POST /api/v1/reviews` - Create review (technician)
- `POST /api/v1/reviews/{review_id}/approve` - Approve sample (technician)
- `POST /api/v1/reviews/{review_id}/reject` - Reject sample (technician)
- `POST /api/v1/reviews/{review_id}/approve-result` - Approve result (technician)
- `POST /api/v1/reviews/{review_id}/reject-result` - Reject result (technician)
- `POST /api/v1/reviews/{review_id}/escalate` - Escalate to pathologist (technician)

## Multi-Tenancy

All operations are tenant-scoped:
- Tenant ID extracted from JWT token
- Automatic filtering in all repository queries
- Unique constraints include tenant_id
- Complete data isolation between tenants

## Default Verification Settings

New tenants are initialized with default settings for common tests:

| Test Code | Test Name | Ref Low | Ref High | Crit Low | Crit High |
|-----------|-----------|---------|----------|----------|-----------|
| GLU | Glucose | 70 | 100 | 40 | 400 |
| WBC | White Blood Count | 4.5 | 11.0 | 2.0 | 30.0 |
| HGB | Hemoglobin | 12.0 | 16.0 | 7.0 | 20.0 |
| PLT | Platelets | 150 | 400 | 50 | 1000 |
| NA | Sodium | 136 | 145 | 120 | 160 |
| K | Potassium | 3.5 | 5.0 | 2.5 | 6.5 |

## Performance Characteristics

- Auto-verification: <1 second per result
- Review queue: <2 seconds to load
- Rule evaluation: <100ms per result
- Batch verification: 1000+ results
- Supports 10+ concurrent tenants
- Scales to 50,000+ results per tenant

## Dependencies

- **Framework:** FastAPI for HTTP API
- **Database:** PostgreSQL (production), SQLite (testing)
- **ORM:** SQLModel for type-safe database operations
- **Validation:** Pydantic for request/response models
- **Testing:** pytest with parametrized fixtures
- **Auth:** JWT tokens with tenant context

## Testing Strategy

- **Shared Tests:** Repository contract tests against both adapters
- **Unit Tests:** Service layer with mocked dependencies
- **Integration Tests:** PostgreSQL-specific scenarios
- **Parametrized Fixtures:** Both in-memory and PostgreSQL tested identically

Each test runs with both adapters, ensuring consistent behavior.

## Monitoring & Logging

- Structured logging at INFO, DEBUG, and ERROR levels
- Request/response logging for audit trails
- Error tracking with context
- Performance metrics available via Prometheus

## References

- [SPECIFICATION-VERIFICATION.md](../../SPECIFICATION-VERIFICATION.md) - Complete feature specification
- [PROPOSED-ARCHITECTURE.md](../../PROPOSED-ARCHITECTURE.md) - Service architecture overview
- [ARCHITECTURE-CORE.md](../../ARCHITECTURE-CORE.md) - Hexagonal architecture principles
- [ARCHITECTURE-MULTITENANCY.md](../../ARCHITECTURE-MULTITENANCY.md) - Multi-tenancy patterns

