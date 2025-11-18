# Architecture Core Principles

This document defines the essential architectural patterns and principles. It serves as the foundation for building maintainable, testable applications.

---

## 1. Hexagonal Architecture (Ports and Adapters)

### Why This Approach
Hexagonal Architecture ensures that business logic remains independent of external infrastructure (databases, APIs, message brokers). This enables:
- Easy testing with in-memory implementations
- Technology swapping without rewriting business logic
- Same code running in different environments (local, Docker, production)

### The Rule
**Core business logic (services) must NEVER depend on concrete infrastructure implementations.**

Instead:
- **Services** depend only on abstract **Ports** (interfaces)
- **Adapters** implement those Ports for specific technologies
- **Dependency Injection** wires adapters into services at startup

### Code Organization

```
services/        → Business logic (domain operations)
ports/           → Abstract contracts (interfaces)
adapters/        → Concrete implementations (PostgreSQL, in-memory, external APIs, etc.)
models/          → Data models (domain entities)
api/             → HTTP endpoints (request/response handling)
exceptions/      → Domain-specific errors
```

**Critical Rule:** Services never import from `api/` or `adapters/`. Services only import from `models/` and other `services/`, and receive dependencies (Ports) via constructor injection.

---

## 2. The Four-Step Dependency Injection Pattern

Follow this pattern for **every external dependency** (databases, message queues, external APIs, file systems, etc.).

### Step 1: Define the Port (Interface)

**Location:** `/app/ports/`

```python
# ports/product_repository.py
import abc
from app.models import Product

class IProductRepository(abc.ABC):
    """Contract for product data persistence."""
    
    @abc.abstractmethod
    def create(self, product: Product) -> Product:
        """Create a new product."""
        pass

    @abc.abstractmethod
    def get_by_id(self, product_id: str) -> Product | None:
        """Retrieve a product by ID."""
        pass
```

### Step 2: Create Adapters

**Location:** `/app/adapters/`

Create at least two implementations:
1. **Production adapter** (PostgreSQL, RabbitMQ, Stripe, etc.)
2. **Test adapter** (in-memory, mock, stub)

```python
# adapters/postgres_product_repository.py
class PostgresProductRepository(IProductRepository):
    def __init__(self, session: Session):
        self._session = session
    
    def create(self, product: Product) -> Product:
        self._session.add(product)
        self._session.commit()
        return product

# adapters/in_memory_product_repository.py
class InMemoryProductRepository(IProductRepository):
    def __init__(self):
        self._products: dict[str, Product] = {}
    
    def create(self, product: Product) -> Product:
        self._products[product.id] = product
        return product
```

### Step 3: Inject Interface into Services

**Location:** `/app/services/`

Services depend on **Ports only**.

```python
# services/order_service.py
class OrderService:
    def __init__(
        self,
        order_repo: IOrderRepository,
        product_repo: IProductRepository
    ):
        """Depends on INTERFACES, not concrete classes."""
        self._order_repo = order_repo
        self._product_repo = product_repo
    
    def create_order(self, user_id: str, items: list[OrderItem]) -> Order:
        """Business logic for creating an order."""
        # Validate, create, persist
        order = Order(user_id=user_id, items=items)
        return self._order_repo.create(order)
```

### Step 4: Wire Dependencies (Composition Root)

**Location:** `/app/dependencies.py`

This is the **only place** where concrete implementations are chosen.

```python
# dependencies.py
from app.config import AppSettings

def get_product_repository(settings: AppSettings) -> IProductRepository:
    if settings.use_real_database:
        return PostgresProductRepository(get_db_session())
    else:
        return InMemoryProductRepository()
```

---

## 3. Synchronous vs Asynchronous Communication

### When to Use Sync (Request-Response)
Use synchronous endpoints when the client needs an immediate response:
- GET requests (queries)
- POST/PUT requests where the client needs confirmation
- Operations that complete quickly (<1 second)

```python
@router.post("/orders")
def create_order(order_data: OrderCreate) -> OrderResponse:
    """Synchronous: returns the created order immediately."""
    order = order_service.create_order(order_data)
    return OrderResponse.from_domain(order)
```

### When to Use Async (Fire-and-Forget)
Use asynchronous endpoints when:
- Operation takes significant time (>1 second)
- Client doesn't need to wait for completion
- Operation can be processed in background

```python
@router.post("/orders/{order_id}/fulfill", status_code=202)
def fulfill_order(order_id: str) -> AcceptedResponse:
    """Async: accepts request, processes in background."""
    task_queue.enqueue(fulfill_order_task, order_id)
    return AcceptedResponse(message="Order fulfillment started", task_id=task_id)
```

**Pattern:**
- Sync endpoints return `200 OK` with response body
- Async endpoints return `202 Accepted` with task/tracking ID
- Provide a separate endpoint to check task status if needed

---

## 4. Multi-Tenancy (If Applicable)

### When Multi-Tenancy Applies
If your application serves multiple isolated customers (tenants) who must not access each other's data.

**Skip this section if:** Your application has no tenant concept or uses a different isolation strategy.

### Rules for Multi-Tenant Applications

1. **Tenant Context in Every Request**
   - Extract tenant ID from JWT, header, or URL
   - Validate tenant access before processing

2. **Automatic Tenant Filtering**
   - All repository queries must filter by tenant ID
   - Enforce filtering at the adapter level, never in service logic
   - Repository interfaces should accept `tenant_id` as a parameter

```python
# Port definition
class IProductRepository(abc.ABC):
    @abc.abstractmethod
    def list_by_tenant(self, tenant_id: str) -> list[Product]:
        pass

# Postgres adapter enforces filtering
class PostgresProductRepository(IProductRepository):
    def list_by_tenant(self, tenant_id: str) -> list[Product]:
        statement = select(Product).where(Product.tenant_id == tenant_id)
        return self._session.exec(statement).all()
```

3. **Test Tenant Isolation**
   - Write tests proving Tenant A cannot access Tenant B's data
   - Test at the repository level

---

## 5. Error Handling

### Custom Exceptions
Define domain-specific exceptions in `/app/exceptions/`.

```python
# exceptions/__init__.py
class ProductNotFoundError(Exception):
    """Raised when a product doesn't exist."""
    pass

class InsufficientStockError(Exception):
    """Raised when trying to order more than available stock."""
    pass
```

### HTTP Status Mapping
Map exceptions to appropriate HTTP status codes:

- `200` – Success
- `201` – Created
- `202` – Accepted (async processing)
- `400` – Bad request (validation error)
- `401` – Unauthorized (authentication failed)
- `403` – Forbidden (insufficient permissions)
- `404` – Not found
- `409` – Conflict (duplicate, constraint violation)
- `500` – Server error (unexpected)

```python
# In main.py or router
@app.exception_handler(ProductNotFoundError)
def product_not_found_handler(request: Request, exc: ProductNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})
```

---

## 6. Configuration Management

Use environment-specific configuration with a single settings class.

```python
# config.py
from pydantic_settings import BaseSettings

class AppSettings(BaseSettings):
    # Deployment
    environment: str = "local"  # local, docker, production
    
    # Database
    database_url: str = "sqlite:///./test.db"
    
    # Security
    secret_key: str = "dev-secret-key"
    
    # Feature flags
    use_real_database: bool = False
    enable_async_tasks: bool = False
    
    class Config:
        env_file = ".env"
```

**Environment Files:**
- `.env.local` – Fast iteration (SQLite, in-memory)
- `.env.docker` – Realistic testing (PostgreSQL, RabbitMQ)
- `.env.production` – Production config (managed services, secrets)

---

## 7. Testing Strategy

### Unit Tests (Fast, No External Dependencies)
Use in-memory adapters. Tests should run in <1 second.

```python
def test_create_order_with_sufficient_stock():
    # Arrange
    product_repo = InMemoryProductRepository()
    order_repo = InMemoryOrderRepository()
    service = OrderService(order_repo, product_repo)
    
    product = Product(id="1", stock=10)
    product_repo.create(product)
    
    # Act
    order = service.create_order("user-1", [OrderItem(product_id="1", quantity=2)])
    
    # Assert
    assert order.id is not None
    assert product_repo.get_by_id("1").stock == 8
```

### Integration Tests (Realistic, With Real Services)
Use Docker Compose to spin up real databases, message queues, etc.

```bash
docker-compose -f docker-compose.test.yml up
pytest tests/integration/
```

### Test Isolation Rules
- Each test must be independent (no shared state)
- Use fixtures to provide clean instances
- Tests should clean up after themselves

### Shared Tests (Run Same Tests Against Multiple Adapters)
Use pytest parametrization to run repository tests against both in-memory and PostgreSQL adapters without code duplication.

**Pattern:**
- Write tests once in `tests/shared/`
- Use parametrized fixtures in `conftest.py`
- Tests automatically run with all adapters

**Setup:**

1. Create parametrized fixture:
```python
# tests/conftest.py
@pytest.fixture(params=["in_memory", "postgres"], ids=["InMemory", "PostgreSQL"])
def user_repo(request, in_memory_user_repo):
    if request.param == "in_memory":
        return in_memory_user_repo
    else:
        try:
            return request.getfixturevalue("postgres_user_repo")
        except:
            pytest.skip("PostgreSQL not available")
```

2. Write tests using the port interface:
```python
# tests/shared/test_user_repository.py
def test_create_user(user_repo: IUserRepository):
    """Runs with BOTH in-memory and PostgreSQL automatically."""
    user = User(username="john")
    created = user_repo.create(user)
    assert created.id is not None
```

3. Result: Each test runs twice (once per adapter)
```
test_create_user[InMemory] PASSED
test_create_user[PostgreSQL] PASSED
```

**File Structure:**
```
tests/
├── conftest.py          # Parametrized fixtures
├── shared/              # Tests that work with any adapter
│   └── test_*_repository.py
└── unit/                # Service tests
```

**Commands:**
```bash
pytest tests/shared/ -v              # All adapters
pytest tests/shared/ -k "InMemory"   # In-memory only (fast)
pytest tests/shared/ -k "PostgreSQL" # PostgreSQL only
```

---

## 8. Project Structure

```
app/
├── main.py                    # Application entry point
├── config.py                  # Settings
├── dependencies.py            # Dependency injection (composition root)
│
├── models/                    # Domain entities
│   ├── user.py
│   ├── product.py
│   └── order.py
│
├── ports/                     # Abstract interfaces
│   ├── user_repository.py
│   ├── product_repository.py
│   └── payment_gateway.py
│
├── adapters/                  # Concrete implementations
│   ├── postgres_*.py          # Production adapters
│   ├── in_memory_*.py         # Test adapters
│   └── stripe_payment.py      # External service adapters
│
├── services/                  # Business logic
│   ├── user_service.py
│   ├── product_service.py
│   └── order_service.py
│
├── api/                       # HTTP layer
│   ├── users.py
│   ├── products.py
│   └── orders.py
│
├── exceptions/                # Domain exceptions
│   └── __init__.py
│
└── tasks/                     # Background jobs (if using async processing)
    └── order_fulfillment.py

tests/
├── conftest.py                # Test fixtures
├── unit/                      # Fast tests with in-memory adapters
└── integration/               # Tests with real infrastructure
```

---

## 9. Code Quality Standards

### Naming Conventions
- **Interfaces (Ports):** Prefix with `I` → `IProductRepository`
- **Implementations:** Suffix with adapter type → `PostgresProductRepository`
- **Services:** Suffix with `Service` → `OrderService`
- **Models:** Domain entities → `User`, `Product`, `Order`

### Type Hints
All public functions must have type hints.

```python
def create_order(user_id: str, items: list[OrderItem]) -> Order:
    """Create a new order."""
    ...
```

### Documentation
- Every Port must have a docstring explaining its contract
- Services must document public methods
- Complex logic needs inline comments explaining "why"

---

## 10. Implementation Checklist

When implementing a feature:

- [ ] Define Port(s) for any external dependency
- [ ] Create at least 2 adapters (production + in-memory)
- [ ] Write Service that depends only on Ports
- [ ] Add HTTP endpoints in `/api`
- [ ] Write unit tests with in-memory adapters
- [ ] Add domain models
- [ ] Define custom exceptions
- [ ] Map exceptions to HTTP status codes
- [ ] Add type hints to all functions
- [ ] Document Ports and Services
- [ ] Validate inputs with Pydantic (if using FastAPI)
- [ ] If multi-tenant: ensure tenant isolation and test it

---

## 11. Quick Reference

| What | Where |
|------|-------|
| Domain models | `/app/models/` |
| Interfaces | `/app/ports/` |
| Production adapters | `/app/adapters/*_postgres.py`, `/app/adapters/*_rabbitmq.py` |
| Test adapters | `/app/adapters/in_memory_*.py` |
| Business logic | `/app/services/` |
| HTTP endpoints | `/app/api/` |
| Background tasks | `/app/tasks/` |
| Exceptions | `/app/exceptions/` |
| DI setup | `/app/dependencies.py` |
| Configuration | `/app/config.py` |
| Tests | `/tests/` |

---

## When to Deviate

This architecture is a **starting point, not a prison**. You may deviate when:

- **Simple CRUD apps:** May not need full Hexagonal Architecture
- **No external dependencies:** Don't create Ports/Adapters for internal logic
- **Proven alternative patterns:** If you have a better approach, document it
- **Performance critical:** Sometimes direct database access is justified

**Rule:** If you deviate, document WHY in the code or a separate `DECISIONS.md` file.

---

*This document is the source of truth for architectural patterns. Follow these principles consistently, but adapt to your specific needs.*
