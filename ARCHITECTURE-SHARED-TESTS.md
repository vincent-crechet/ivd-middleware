# Shared Tests - No Code Duplication

This document explains how the same test code runs against both in-memory and PostgreSQL adapters without duplication.

## The Problem

In hexagonal architecture, we have multiple implementations of the same interface:
- **In-memory adapters** for fast unit tests
- **PostgreSQL adapters** for integration tests

Without proper setup, we'd need to write identical tests twice:
```
tests/unit/test_tenant_repository.py          # Tests with in-memory
tests/integration/test_postgres_tenant_repo.py # Same tests with PostgreSQL
```

This leads to:
- Code duplication
- Maintenance burden
- Tests getting out of sync

## The Solution: Parametrized Fixtures

We use pytest's **fixture parametrization** to run the same test code with different adapters.

### How It Works

#### 1. Parametrized Fixtures in `conftest.py`

```python
@pytest.fixture(params=["in_memory", "postgres"], ids=["InMemory", "PostgreSQL"])
def tenant_repo(request, in_memory_tenant_repo):
    """Runs tests twice: once with each adapter."""
    if request.param == "in_memory":
        return in_memory_tenant_repo
    elif request.param == "postgres":
        try:
            return request.getfixturevalue("postgres_tenant_repo")
        except Exception:
            pytest.skip("PostgreSQL not available")
```

#### 2. Write Tests Once in `tests/shared/`

```python
def test_create_tenant(tenant_repo: ITenantRepository):
    """This test automatically runs with BOTH adapters!"""
    tenant = Tenant(name="Acme Corp")
    created = tenant_repo.create(tenant)

    assert created.id is not None
    assert created.name == "Acme Corp"
```

#### 3. Pytest Automatically Runs Tests Multiple Times

When you run `pytest tests/shared/test_tenant_repository.py::test_create_tenant`:

```
test_create_tenant[InMemory] PASSED     # ✓ Runs with in-memory adapter
test_create_tenant[PostgreSQL] PASSED   # ✓ Runs with PostgreSQL adapter
```

## Benefits

### ✅ Zero Code Duplication
Write each test **once**, runs with **both adapters** automatically.

### ✅ Guaranteed Consistency
Both adapters are tested with **identical logic**.

### ✅ Easy to Add More Adapters
Add a new adapter (e.g., MongoDB)? Just update the fixture:
```python
@pytest.fixture(params=["in_memory", "postgres", "mongodb"])
def tenant_repo(request, ...):
    # Add mongodb case
```

All tests automatically run against the new adapter!

### ✅ Graceful Degradation
If PostgreSQL isn't available, tests skip gracefully:
```
test_create_tenant[InMemory] PASSED     # ✓ Still runs
test_create_tenant[PostgreSQL] SKIPPED  # ⊘ Skips if DB unavailable
```

## Running the Tests

### Run All Shared Tests (In-Memory + PostgreSQL if available)
```bash
pytest tests/shared/ -v
```

### Run Only In-Memory Tests
```bash
pytest tests/shared/ -k "InMemory"
```

### Run Only PostgreSQL Tests
```bash
# Start PostgreSQL first
docker-compose -f docker-compose.test.yml up -d

# Run PostgreSQL tests
pytest tests/shared/ -k "PostgreSQL"
```

## Test Results

With PostgreSQL available:
```
tests/shared/test_tenant_repository.py::test_create_tenant[InMemory] PASSED
tests/shared/test_tenant_repository.py::test_create_tenant[PostgreSQL] PASSED
tests/shared/test_tenant_repository.py::test_get_tenant_by_id[InMemory] PASSED
tests/shared/test_tenant_repository.py::test_get_tenant_by_id[PostgreSQL] PASSED
...
```

Without PostgreSQL:
```
tests/shared/test_tenant_repository.py::test_create_tenant[InMemory] PASSED
tests/shared/test_tenant_repository.py::test_create_tenant[PostgreSQL] SKIPPED
tests/shared/test_tenant_repository.py::test_get_tenant_by_id[InMemory] PASSED
tests/shared/test_tenant_repository.py::test_get_tenant_by_id[PostgreSQL] SKIPPED
...
```

## Architecture Benefits

This approach perfectly demonstrates **hexagonal architecture** principles:

### Ports (Interfaces)
```python
class ITenantRepository(abc.ABC):
    @abc.abstractmethod
    def create(self, tenant: Tenant) -> Tenant:
        pass
```

### Adapters (Implementations)
```python
class InMemoryTenantRepository(ITenantRepository):
    def create(self, tenant: Tenant) -> Tenant:
        # In-memory implementation

class PostgresTenantRepository(ITenantRepository):
    def create(self, tenant: Tenant) -> Tenant:
        # PostgreSQL implementation
```

### Tests Against the Port
```python
def test_create_tenant(tenant_repo: ITenantRepository):
    # Works with ANY implementation of ITenantRepository!
```

## File Structure

```
tests/
├── conftest.py                           # Parametrized fixtures
├── shared/                               # Tests that work with any adapter
│   ├── test_tenant_repository.py         # 11 tests × 2 adapters = 22 test runs
│   └── test_user_repository.py           # 16 tests × 2 adapters = 32 test runs
├── unit/                                 # Legacy unit-only tests
│   ├── test_tenant_service.py            # Service tests
│   └── test_user_service.py              # Service tests
└── integration/                          # PostgreSQL-specific tests
    ├── test_tenant_isolation_postgres.py # Complex isolation scenarios
    └── test_services_postgres.py         # End-to-end tests
```

## When to Use Shared Tests vs Specific Tests

### Use Shared Tests For:
- ✅ Repository CRUD operations
- ✅ Basic validation logic
- ✅ Interface contract verification
- ✅ Any test that applies to ALL implementations

### Use Specific Tests For:
- ✅ PostgreSQL-specific features (transactions, constraints)
- ✅ Performance tests
- ✅ Complex multi-entity scenarios
- ✅ Database-specific error handling

## Adding a New Shared Test

1. **Write the test in `tests/shared/`**:
   ```python
   def test_my_new_feature(tenant_repo: ITenantRepository):
       # Your test code here
       pass
   ```

2. **Run the test**:
   ```bash
   pytest tests/shared/test_tenant_repository.py::test_my_new_feature -v
   ```

3. **See it run with both adapters**:
   ```
   test_my_new_feature[InMemory] PASSED
   test_my_new_feature[PostgreSQL] PASSED
   ```

That's it! No duplication needed.

## Migration Guide

If you have duplicate tests, migrate them:

### Before (Duplicated):
```
tests/unit/test_tenant_repo.py           # 100 lines
tests/integration/test_postgres_tenant.py # 100 lines (same tests!)
```

### After (Shared):
```
tests/shared/test_tenant_repository.py   # 100 lines (runs with both!)
```

**Result**: Cut test code in half, guaranteed consistency!

## Summary

| Approach | Lines of Test Code | Runs Against | Maintenance |
|----------|-------------------|--------------|-------------|
| **Duplicated** | 200 lines | In-memory + PostgreSQL | 2× work |
| **Shared** | 100 lines | In-memory + PostgreSQL | 1× work |

**The shared approach demonstrates the power of hexagonal architecture:**
- Write once, test everywhere
- Adapters are truly interchangeable
- Interface contracts are enforced
- Adding new adapters is trivial

This is the hexagonal architecture testing pattern at its best! 🎯
