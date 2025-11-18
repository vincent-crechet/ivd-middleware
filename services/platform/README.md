# Platform Service

Identity & Multi-Tenancy Service for IVD Middleware.

**📋 Specification:** See [SPECIFICATION-PLATFORM.md](../../SPECIFICATION-PLATFORM.md) for detailed requirements, acceptance criteria, and business rules.

## Responsibility

- Tenant management
- User management with role-based access control
- Authentication (JWT tokens with tenant context)
- Authorization

## Features

- Create and manage laboratory tenants
- User CRUD operations (Admin, Technician, Pathologist roles)
- JWT-based authentication with tenant_id embedded
- Multi-tenant data isolation enforced at repository level

## API Endpoints

### Authentication
- `POST /api/v1/auth/login` - Authenticate and get JWT token
- `GET /api/v1/auth/me` - Get current user info

### Tenants
- `POST /api/v1/tenants` - Create tenant
- `GET /api/v1/tenants/{id}` - Get tenant
- `GET /api/v1/tenants` - List tenants
- `PUT /api/v1/tenants/{id}` - Update tenant
- `DELETE /api/v1/tenants/{id}` - Delete tenant

### Users
- `POST /api/v1/users` - Create user (tenant from JWT)
- `GET /api/v1/users/{id}` - Get user
- `GET /api/v1/users` - List users
- `PUT /api/v1/users/{id}` - Update user
- `POST /api/v1/users/{id}/password` - Change password
- `DELETE /api/v1/users/{id}` - Delete user

## Running Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run the service
uvicorn app.main:app --reload

# Run tests
pytest

# Run with coverage
pytest --cov=app
```

## Running with Docker

```bash
# Build image
docker build -t platform-service .

# Run container
docker run -p 8000:8000 platform-service
```

## Architecture

Follows Hexagonal Architecture:
- **Models**: Domain entities (Tenant, User)
- **Ports**: Abstract interfaces (repositories, services)
- **Adapters**: Concrete implementations (PostgreSQL, in-memory, bcrypt, JWT)
- **Services**: Business logic
- **API**: HTTP endpoints (FastAPI)

Multi-tenancy enforced at repository level with automatic tenant_id filtering.
