# Integration Tests with PostgreSQL

This document explains how to run integration tests with a real PostgreSQL database.

## Overview

The integration tests verify that:
- PostgreSQL adapters work correctly with a real database
- Tenant isolation is enforced at the database level
- Services persist data correctly
- Multi-tenant scenarios work end-to-end

## Test Coverage

### Repository Tests

**Tenant Repository** (`test_postgres_tenant_repository.py`):
- Create, read, update, delete tenants
- Duplicate name validation
- Tenant listing

**User Repository** (`test_postgres_user_repository.py`):
- Create, read, update, delete users
- Duplicate username validation (per tenant)
- Same username in different tenants allowed
- Tenant isolation on all operations

### Tenant Isolation Tests

**Comprehensive Isolation** (`test_tenant_isolation_postgres.py`):
- Get user by ID enforces tenant isolation
- List users only returns tenant's users
- Delete user enforces tenant isolation
- Same username in different tenants are completely isolated
- Cross-tenant data leak prevention

### Service Tests

**Services with PostgreSQL** (`test_services_postgres.py`):
- Create tenant with admin user persists to database
- User authentication with database
- Wrong password fails
- Supervisor authorization
- Multi-tenant isolation
- Password change persists
- User deactivation persists

## Prerequisites

1. **Docker** and **Docker Compose** installed
2. **Python 3.10+**
3. **Dependencies** installed: `pip install -r requirements.txt`

## Running Integration Tests

### Method 1: Using the Helper Script (Recommended)

```bash
./run_integration_tests.sh
```

This script will:
1. Start PostgreSQL in a Docker container
2. Wait for the database to be ready
3. Run all integration tests
4. Show results

### Method 2: Manual Setup

```bash
# Start PostgreSQL
docker-compose -f docker-compose.test.yml up -d

# Wait for PostgreSQL to be ready
until docker exec ivd_middleware_test_db pg_isready -U postgres; do
  sleep 2
done

# Run integration tests
pytest tests/integration/ -v

# Stop PostgreSQL when done
docker-compose -f docker-compose.test.yml down
```

### Method 3: Run Specific Test Files

```bash
# Run only tenant repository tests
pytest tests/integration/test_postgres_tenant_repository.py -v

# Run only user repository tests
pytest tests/integration/test_postgres_user_repository.py -v

# Run only tenant isolation tests
pytest tests/integration/test_tenant_isolation_postgres.py -v

# Run only service tests
pytest tests/integration/test_services_postgres.py -v
```

## Database Configuration

The integration tests use the following PostgreSQL connection:

- **Host**: localhost
- **Port**: 5432
- **Database**: ivd_middleware_test
- **Username**: postgres
- **Password**: postgres

You can override this by setting the `TEST_DATABASE_URL` environment variable:

```bash
export TEST_DATABASE_URL="postgresql://user:pass@host:port/dbname"
pytest tests/integration/ -v
```

## Test Isolation

Each test function runs in its own transaction that is rolled back after the test completes. This ensures:
- Tests don't interfere with each other
- Database is clean for each test
- Fast test execution (no database cleanup needed)

## Troubleshooting

### PostgreSQL Connection Failed

If tests fail with connection errors:

```bash
# Check if PostgreSQL is running
docker ps | grep ivd_middleware_test_db

# Check PostgreSQL logs
docker logs ivd_middleware_test_db

# Restart PostgreSQL
docker-compose -f docker-compose.test.yml restart
```

### Port 5432 Already in Use

If you have another PostgreSQL instance running:

1. Stop your local PostgreSQL:
   ```bash
   sudo service postgresql stop
   ```

2. Or change the port in `docker-compose.test.yml`:
   ```yaml
   ports:
     - "5433:5432"  # Use port 5433 instead
   ```

   And update `TEST_DATABASE_URL` accordingly.

### Tests Are Slow

Integration tests are slower than unit tests because they use a real database. To run only fast unit tests:

```bash
pytest tests/unit/ -v
```

## Continuous Integration

For CI/CD pipelines, use the Docker Compose setup:

```yaml
# Example GitHub Actions workflow
- name: Start PostgreSQL
  run: docker-compose -f docker-compose.test.yml up -d

- name: Wait for PostgreSQL
  run: |
    until docker exec ivd_middleware_test_db pg_isready -U postgres; do
      sleep 2
    done

- name: Run Integration Tests
  run: pytest tests/integration/ -v

- name: Stop PostgreSQL
  run: docker-compose -f docker-compose.test.yml down
```

## Test Statistics

Total integration tests: **36 tests**

- Tenant Repository: 11 tests
- User Repository: 16 tests
- Tenant Isolation: 6 tests
- Services with PostgreSQL: 9 tests

All tests verify:
- Data persistence
- Tenant isolation
- Business logic with database
- Error handling

## Clean Up

To remove the test database and volumes:

```bash
docker-compose -f docker-compose.test.yml down -v
```

This will delete all test data and free up disk space.
