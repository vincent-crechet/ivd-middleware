# IVD Middleware - Tenant and User Management Service

A multi-tenant user management service built with FastAPI following hexagonal architecture principles.

## Features

### Requirements Implementation

This service implements the following requirements from the specification:

1. **User Management**: Users are defined with username, password, and a supervisor attribute
2. **Supervisor Authorization**: Only supervisors can change configuration (enforced via API authorization)
3. **Tenant Creation**: When creating a new tenant, a first supervisor user is automatically created

### Architecture

- **Hexagonal Architecture (Ports and Adapters)**: Clean separation between business logic and infrastructure
- **Multi-Tenancy**: Strict tenant isolation with automatic filtering at repository level
- **Dependency Injection**: Easy switching between in-memory and PostgreSQL implementations
- **Type Safety**: Full type hints throughout the codebase

## Project Structure

```
ivd_middleware/
├── app/
│   ├── models/              # Domain models (Tenant, User)
│   ├── ports/               # Abstract interfaces
│   ├── adapters/            # Concrete implementations
│   │   ├── in_memory_*.py   # In-memory repositories for testing
│   │   └── postgres_*.py    # PostgreSQL repositories for production
│   ├── services/            # Business logic
│   ├── api/                 # HTTP endpoints
│   ├── exceptions/          # Domain exceptions
│   ├── config.py            # Configuration
│   ├── dependencies.py      # Dependency injection
│   └── main.py              # Application entry point
├── tests/
│   ├── unit/                # Unit tests with in-memory adapters
│   └── integration/         # Integration tests (future)
├── requirements.txt
└── README.md
```

## Installation

### Prerequisites

- Python 3.10+
- PostgreSQL (optional, for production mode)

### Setup

1. Clone the repository:
```bash
cd /home/vcrechet/projects/ivd_middleware
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
# or
venv\Scripts\activate  # On Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

### Development Mode (In-Memory)

For quick development without a database:

```bash
python -m app.main
```

or

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

### Production Mode (PostgreSQL)

1. Create a `.env` file:
```bash
USE_REAL_DATABASE=true
DATABASE_URL=postgresql://user:password@localhost:5432/ivd_middleware
SECRET_KEY=your-secret-key-here
ENVIRONMENT=production
```

2. Run the application:
```bash
python -m app.main
```

## API Documentation

Once the application is running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## API Endpoints

### Tenants

- `POST /tenants` - Create a new tenant with admin user
- `GET /tenants` - List all tenants
- `GET /tenants/{tenant_id}` - Get a tenant by ID
- `PATCH /tenants/{tenant_id}` - Update a tenant
- `POST /tenants/{tenant_id}/activate` - Activate a tenant
- `POST /tenants/{tenant_id}/deactivate` - Deactivate a tenant
- `DELETE /tenants/{tenant_id}` - Delete a tenant

### Users

All user endpoints require the `X-Tenant-ID` header for tenant isolation.

- `POST /users` - Create a new user
- `POST /users/login` - Authenticate a user
- `GET /users` - List all users in the tenant
- `GET /users/{user_id}` - Get a user by ID
- `PATCH /users/{user_id}` - Update a user
- `POST /users/{user_id}/change-password` - Change password
- `GET /users/{user_id}/is-supervisor` - Check supervisor status
- `POST /users/{user_id}/deactivate` - Deactivate a user
- `DELETE /users/{user_id}` - Delete a user

## Usage Examples

### Creating a Tenant

```bash
curl -X POST "http://localhost:8000/tenants" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "description": "A test company",
    "admin_username": "admin",
    "admin_password": "SecurePassword123",
    "admin_email": "admin@acme.com"
  }'
```

Response:
```json
{
  "tenant": {
    "id": "uuid-here",
    "name": "Acme Corp",
    "is_active": true,
    "description": "A test company",
    "created_at": "2025-11-17T...",
    "updated_at": "2025-11-17T..."
  },
  "admin_user": {
    "id": "uuid-here",
    "tenant_id": "tenant-uuid",
    "username": "admin",
    "is_supervisor": true,
    "is_active": true,
    "email": "admin@acme.com",
    "created_at": "2025-11-17T...",
    "updated_at": "2025-11-17T..."
  }
}
```

### Creating a User

```bash
curl -X POST "http://localhost:8000/users" \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: tenant-uuid-here" \
  -d '{
    "username": "john",
    "password": "Password123",
    "is_supervisor": false,
    "email": "john@acme.com",
    "full_name": "John Doe"
  }'
```

### Authenticating a User

```bash
curl -X POST "http://localhost:8000/users/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "SecurePassword123",
    "tenant_id": "tenant-uuid-here"
  }'
```

### Checking Supervisor Status

```bash
curl -X GET "http://localhost:8000/users/{user_id}/is-supervisor" \
  -H "X-Tenant-ID: tenant-uuid-here"
```

## Running Tests

```bash
pytest tests/
```

Run with coverage:
```bash
pytest tests/ --cov=app --cov-report=html
```

## Configuration

Configuration is managed through environment variables or `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `ENVIRONMENT` | local | Environment: local, docker, production |
| `USE_REAL_DATABASE` | False | Use PostgreSQL (True) or in-memory (False) |
| `DATABASE_URL` | sqlite:///./ivd_middleware.db | Database connection string |
| `SECRET_KEY` | dev-secret-key... | Secret key for security |
| `ENABLE_CORS` | True | Enable CORS middleware |

## Security Notes

### Current Implementation

- Passwords are hashed using SHA-256 (for demonstration)
- User authentication returns user details (not JWT tokens)

### Production Recommendations

1. **Use Bcrypt or Argon2** for password hashing instead of SHA-256
2. **Implement JWT tokens** for authentication instead of returning user details
3. **Add rate limiting** to prevent brute force attacks
4. **Use HTTPS** in production
5. **Implement proper CORS** configuration (not allow all origins)
6. **Add request validation** and input sanitization
7. **Implement audit logging** for security events

## Multi-Tenancy

This service implements strict tenant isolation:

- All user data is scoped to a tenant
- Users can only access data within their tenant
- Repository layer enforces filtering automatically
- Tests prove tenant A cannot access tenant B's data

See `tests/unit/test_tenant_isolation.py` for isolation tests.

## Architecture Principles

### Hexagonal Architecture

- **Ports**: Abstract interfaces defining contracts
- **Adapters**: Concrete implementations (PostgreSQL, in-memory)
- **Services**: Business logic, independent of infrastructure
- **API**: HTTP layer, thin controllers

### Dependency Injection

All dependencies are injected via `dependencies.py`:
- Easy to swap implementations
- Testable with in-memory adapters
- No hard dependencies in business logic

## Future Enhancements

- [ ] JWT-based authentication
- [ ] Role-based access control (RBAC)
- [ ] Audit logging
- [ ] Password strength validation
- [ ] Email verification
- [ ] Two-factor authentication (2FA)
- [ ] API rate limiting
- [ ] Docker Compose setup
- [ ] CI/CD pipeline
- [ ] Integration tests

## License

MIT License

## Support

For issues or questions, please open an issue in the repository.
