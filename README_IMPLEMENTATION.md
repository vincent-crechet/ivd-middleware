# IVD Middleware - Implementation Guide

Multi-tenant platform for automated laboratory result verification and management.

## Project Structure

```
ivd_middleware/
├── services/                    # Backend microservices
│   ├── platform/                # Platform Service (Identity & Multi-Tenancy)
│   │   ├── app/
│   │   │   ├── models/          # Domain entities (Tenant, User)
│   │   │   ├── ports/           # Abstract interfaces
│   │   │   ├── adapters/        # Concrete implementations
│   │   │   ├── services/        # Business logic
│   │   │   ├── api/             # HTTP endpoints
│   │   │   ├── exceptions/      # Domain exceptions
│   │   │   ├── config.py        # Configuration
│   │   │   ├── dependencies.py  # Dependency injection
│   │   │   └── main.py          # Application entry point
│   │   ├── tests/               # Unit, integration, shared tests
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── README.md
│   │
│   ├── lis_integration/         # LIS Integration Service
│   │   ├── app/
│   │   │   ├── models/          # Sample, Result models
│   │   │   ├── ports/           # Repository, LIS adapter interfaces
│   │   │   ├── adapters/
│   │   │   │   └── lis_adapters/ # Mock, File, REST adapters
│   │   │   ├── tasks/           # Background jobs (pull model)
│   │   │   └── ...
│   │   └── ...
│   │
│   ├── verification/            # Verification & Review Service
│   │   ├── app/
│   │   │   ├── models/          # Review, AutoVerificationSettings
│   │   │   ├── adapters/
│   │   │   │   └── verification_engine/ # Rule implementations
│   │   │   └── ...
│   │   └── ...
│   │
│   └── api_gateway/             # API Gateway (Optional)
│       ├── app/
│       │   └── main.py          # Request routing
│       └── ...
│
├── web_apps/                    # Frontend applications
│   ├── laboratory_portal/       # Main SPA (all lab users)
│   │   ├── src/
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   └── system_admin_portal/     # System operators (optional)
│       └── ...
│
├── shared/                      # Shared code
│   └── models/                  # Shared domain models
│
├── docker-compose.yml           # Local development environment
├── SPECIFICATION.md             # Product specification
├── ARCHITECTURE-*.md            # Architecture documentation
├── PROPOSED-ARCHITECTURE.md     # This implementation design
└── README_IMPLEMENTATION.md     # This file
```

## Architecture Overview

### Backend Services (3 Core Services)

#### 1. Platform Service (Port 8000)
**Responsibility**: Identity & Multi-Tenancy
- Tenant management
- User management (Admin, Technician, Pathologist roles)
- JWT authentication with tenant_id
- Role-based access control

**API**: `/api/v1/auth/*`, `/api/v1/tenants/*`, `/api/v1/users/*`

#### 2. LIS Integration Service (Port 8001)
**Responsibility**: Laboratory Information System Integration
- LIS adapters (Mock, File Upload, REST API)
- Push model: Receive orders from LIS
- Pull model: Background jobs to retrieve data
- Sample and result ingestion

**API**: `/api/v1/lis/*`, `/api/v1/samples/*`

#### 3. Verification & Review Service (Port 8002)
**Responsibility**: Auto-verification & Manual Review
- Auto-verification rules (Reference Range, Critical Range, Instrument Flag, Delta Check)
- Manual review workflow (sample-level)
- Review queue management
- Escalation to pathologists

**API**: `/api/v1/verification/*`, `/api/v1/reviews/*`

#### 4. API Gateway (Port 8080) - Optional
**Responsibility**: Single entry point
- Routes requests to appropriate services
- CORS handling
- Can add rate limiting, auth validation

### Frontend Applications

#### 1. Laboratory Portal
Main SPA for all laboratory users with role-based views:
- **Admin**: Tenant config, user management, LIS setup, verification settings
- **Technician**: Review queue, sample search, approve/reject
- **Pathologist**: Escalated reviews, clinical oversight

#### 2. System Admin Portal (Optional)
For platform operators to manage tenants.

## Getting Started

### Prerequisites

- Docker & Docker Compose (recommended)
- OR: Python 3.11+, PostgreSQL 16+, Redis, RabbitMQ
- Node.js 20+ (for web apps)

### Quick Start with Docker

1. **Clone the repository**
```bash
git clone <repository-url>
cd ivd_middleware
```

2. **Start all services with Docker Compose**
```bash
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- RabbitMQ (port 5672, management UI: 15672)
- Platform Service (port 8000)
- LIS Integration Service (port 8001)
- Verification Service (port 8002)
- API Gateway (port 8080)
- Celery worker for background tasks

3. **Access the services**
- API Gateway: http://localhost:8080
- Platform Service: http://localhost:8000/docs
- LIS Integration: http://localhost:8001/docs
- Verification Service: http://localhost:8002/docs
- RabbitMQ Management: http://localhost:15672 (user: ivd_user, password: ivd_password)

4. **View logs**
```bash
docker-compose logs -f
docker-compose logs -f platform
```

5. **Stop services**
```bash
docker-compose down
```

### Running Services Individually

#### Platform Service

```bash
cd services/platform
pip install -r requirements.txt

# Run with in-memory database (fast, for testing)
USE_REAL_DATABASE=false uvicorn app.main:app --reload

# Run with PostgreSQL
DATABASE_URL="postgresql://user:pass@localhost/db" USE_REAL_DATABASE=true uvicorn app.main:app --reload

# Run tests
pytest
pytest --cov=app
```

#### LIS Integration Service

```bash
cd services/lis_integration
pip install -r requirements.txt

# Run API server
uvicorn app.main:app --reload --port 8001

# Run Celery worker (for pull model)
celery -A app.tasks.worker worker --loglevel=info

# Run tests
pytest
```

#### Verification Service

```bash
cd services/verification
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
pytest
```

## Development Workflow

### Adding a New Feature

Follow the Hexagonal Architecture pattern (see ARCHITECTURE-CORE.md):

1. **Define Port (Interface)** in `/app/ports/`
2. **Create Adapters** (PostgreSQL + In-Memory) in `/app/adapters/`
3. **Implement Service** (business logic) in `/app/services/`
4. **Add API Endpoints** in `/app/api/`
5. **Wire Dependencies** in `/app/dependencies.py`
6. **Write Tests**:
   - Unit tests with in-memory adapters
   - Integration tests with real database
   - Shared tests that run against all adapters

### Testing Strategy

**Unit Tests** (Fast, no external dependencies)
```bash
pytest tests/unit/ -v
```

**Integration Tests** (With real database)
```bash
docker-compose -f docker-compose.test.yml up -d postgres
pytest tests/integration/ -v
```

**Shared Tests** (Run same tests against all adapters)
```bash
pytest tests/shared/ -v
pytest tests/shared/ -k "InMemory"   # Only in-memory
pytest tests/shared/ -k "PostgreSQL" # Only PostgreSQL
```

## Multi-Tenancy

All services enforce multi-tenant isolation:

1. **JWT Token** includes `tenant_id`
2. **API Endpoints** extract tenant_id from token
3. **Services** pass tenant_id to repositories
4. **Repositories** automatically filter by tenant_id
5. **Tests** verify tenant isolation

Example flow:
```
User logs in → JWT with tenant_id → Request includes JWT →
Dependency extracts tenant_id → Service uses tenant_id →
Repository filters by tenant_id
```

## Service Communication

**For MVP**: Services share PostgreSQL database
- Simpler for development
- Easier transactions
- Services access own tables + shared tables (samples, results)

**Future**: Event-driven architecture
- Integration Service publishes `SampleIngested` events
- Verification Service subscribes and triggers auto-verification
- Better scaling, loose coupling

## Database Schema

**Platform Service owns**:
- `tenants`
- `users`

**LIS Integration owns**:
- `lis_configurations`
- `samples` (created)
- `results` (created)

**Verification Service owns**:
- `auto_verification_settings`
- `reviews`
- `review_decisions`

**Shared**:
- `samples` (created by LIS, read by Verification)
- `results` (created by LIS, updated by Verification)

## Configuration

Each service uses `pydantic-settings` for configuration:

```python
# .env file
ENVIRONMENT=local          # local, docker, production
USE_REAL_DATABASE=false
DATABASE_URL=postgresql://user:pass@localhost/db
SECRET_KEY=your-secret-key
```

## API Documentation

Each service exposes interactive API docs:
- Platform: http://localhost:8000/docs
- LIS Integration: http://localhost:8001/docs
- Verification: http://localhost:8002/docs

## Deployment

### Docker Compose (Development/Testing)
```bash
docker-compose up
```

### Kubernetes (Production)
See deployment manifests in `/k8s/` (to be created)

### Environment Variables

**Production checklist**:
- [ ] Change `SECRET_KEY` to strong random value
- [ ] Use managed PostgreSQL with proper credentials
- [ ] Configure CORS origins appropriately
- [ ] Set `ENVIRONMENT=production`
- [ ] Enable database connection pooling
- [ ] Configure logging to external service

## Next Steps

### Immediate Tasks (MVP - P0)

1. **Complete LIS Integration Service**
   - Implement Sample and Result models
   - Create repository implementations
   - Build Mock LIS adapter
   - Add push endpoint for receiving orders

2. **Complete Verification Service**
   - Implement auto-verification rules
   - Create review workflow
   - Build verification engine adapters

3. **Implement First Admin User Creation**
   - Add endpoint to create tenant + first admin user atomically
   - See SPECIFICATION.md Feature 1 requirements

4. **Build Laboratory Portal Frontend**
   - Set up Vue.js project
   - Implement authentication
   - Create admin dashboard
   - Create review queue for technicians

5. **End-to-End Testing**
   - Create tenant
   - Add users
   - Configure LIS
   - Send sample data
   - Auto-verify results
   - Manual review workflow

### Phase 2 (P1)

- File upload LIS adapter
- REST API pull model
- Review escalation
- Patient history view
- LIS connection health monitoring

### Phase 3 (P2+)

- Advanced analytics
- Email notifications
- Bulk operations
- Event-driven architecture migration

## Contributing

1. Follow Hexagonal Architecture patterns
2. Write tests (unit + integration)
3. Ensure multi-tenant isolation
4. Document business rules
5. Add type hints to all functions

## Troubleshooting

**Service won't start**:
- Check Docker containers: `docker-compose ps`
- View logs: `docker-compose logs <service-name>`
- Verify ports not in use: `lsof -i :8000`

**Database connection errors**:
- Ensure PostgreSQL is running
- Check DATABASE_URL environment variable
- Verify credentials

**Tests failing**:
- Run with verbose: `pytest -v -s`
- Check test database connection
- Ensure fixtures are properly set up

## Resources

- [SPECIFICATION.md](./SPECIFICATION.md) - Product requirements
- [ARCHITECTURE-CORE.md](./ARCHITECTURE-CORE.md) - Architecture principles
- [ARCHITECTURE-MULTITENANCY.md](./ARCHITECTURE-MULTITENANCY.md) - Multi-tenancy guide
- [PROPOSED-ARCHITECTURE.md](./PROPOSED-ARCHITECTURE.md) - Implementation design
- FastAPI docs: https://fastapi.tiangolo.com
- SQLModel docs: https://sqlmodel.tiangolo.com

## License

[Your License Here]
