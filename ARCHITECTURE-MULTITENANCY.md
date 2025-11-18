# Multi-Tenancy Architecture Guide

**Read this document ONLY if your application serves multiple isolated customers (tenants) who must not access each other's data.**

**Skip this if:** You're building a single-tenant application, a personal tool, or use a different isolation strategy.

---

## 1. What is Multi-Tenancy?

Multi-tenancy means a single application instance serves multiple customers (tenants), with strict data isolation between them.

**Example Use Cases:**
- SaaS applications (each company is a tenant)
- E-commerce platforms (each merchant is a tenant)
- Healthcare systems (each clinic is a tenant)

**Not Multi-Tenant:**
- Internal company tools
- Consumer apps where users share data
- Applications with role-based access only

---

## 2. Core Principles

### 2.1 Tenant Context is Mandatory

Every request MUST carry tenant identification. Without it, the request should be rejected.

**Tenant Identification Methods:**
1. **JWT Token** (Recommended) – Embed `tenant_id` in token payload
2. **Request Header** – Custom header like `X-Tenant-ID`
3. **URL Path** – Extract from URL like `/tenants/{tenant_id}/resources`

### 2.2 Data Isolation at Repository Level

**Critical Rule:** Tenant filtering happens in **adapters**, NEVER in service logic.

**Why:** If service logic handles filtering, a single bug can leak data across tenants. Repositories must enforce isolation automatically.

### 2.3 Test Tenant Isolation

Every repository must have tests proving Tenant A cannot access Tenant B's data, even if they query the same repository.

---

## 3. Implementation Pattern

### Step 1: Extract Tenant Context

Create a dependency that extracts and validates tenant ID from requests.

```python
# dependencies.py
from fastapi import Request, HTTPException

def get_current_tenant_id(request: Request) -> str:
    """Extract and validate tenant ID from request."""
    
    # Option 1: From JWT token
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    payload = verify_jwt_token(token)  # Your JWT verification logic
    tenant_id = payload.get("tenant_id")
    
    # Option 2: From custom header
    # tenant_id = request.headers.get("X-Tenant-ID")
    
    # Option 3: From URL path
    # tenant_id = request.path_params.get("tenant_id")
    
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant ID missing")
    
    # Optional: Verify tenant exists and is active
    # tenant = tenant_service.get_tenant(tenant_id)
    # if not tenant or not tenant.is_active:
    #     raise HTTPException(status_code=403, detail="Invalid tenant")
    
    return tenant_id
```

### Step 2: Inject Tenant ID into Endpoints

Use FastAPI's dependency injection to automatically extract tenant ID.

```python
# api/products.py
from fastapi import APIRouter, Depends

router = APIRouter()

@router.get("/products")
def list_products(
    tenant_id: str = Depends(get_current_tenant_id),
    product_service: ProductService = Depends(get_product_service)
):
    """List products for the authenticated tenant."""
    products = product_service.list_products(tenant_id)
    return products
```

### Step 3: Services Accept Tenant ID

Services receive tenant ID as a parameter and pass it to repositories.

```python
# services/product_service.py
class ProductService:
    def __init__(self, product_repo: IProductRepository):
        self._product_repo = product_repo
    
    def list_products(self, tenant_id: str) -> list[Product]:
        """List products for a specific tenant."""
        return self._product_repo.list_by_tenant(tenant_id)
    
    def create_product(self, tenant_id: str, product_data: dict) -> Product:
        """Create a product for a specific tenant."""
        product = Product(**product_data, tenant_id=tenant_id)
        return self._product_repo.create(product)
```

### Step 4: Repositories Enforce Filtering

**Port Definition:**

```python
# ports/product_repository.py
import abc
from app.models import Product

class IProductRepository(abc.ABC):
    """Repository for product data with tenant isolation."""
    
    @abc.abstractmethod
    def list_by_tenant(self, tenant_id: str) -> list[Product]:
        """List all products for a specific tenant."""
        pass
    
    @abc.abstractmethod
    def get_by_id(self, product_id: str, tenant_id: str) -> Product | None:
        """Get a product by ID, ensuring it belongs to the tenant."""
        pass
    
    @abc.abstractmethod
    def create(self, product: Product) -> Product:
        """Create a product. Product must have tenant_id set."""
        pass
```

**PostgreSQL Adapter (Automatic Filtering):**

```python
# adapters/postgres_product_repository.py
from sqlmodel import Session, select
from app.models import Product

class PostgresProductRepository(IProductRepository):
    def __init__(self, session: Session):
        self._session = session
    
    def list_by_tenant(self, tenant_id: str) -> list[Product]:
        """Automatically filters by tenant_id."""
        statement = select(Product).where(Product.tenant_id == tenant_id)
        return self._session.exec(statement).all()
    
    def get_by_id(self, product_id: str, tenant_id: str) -> Product | None:
        """Ensures product belongs to tenant."""
        statement = select(Product).where(
            Product.id == product_id,
            Product.tenant_id == tenant_id
        )
        return self._session.exec(statement).first()
    
    def create(self, product: Product) -> Product:
        """Validates tenant_id is set before creating."""
        if not product.tenant_id:
            raise ValueError("Product must have a tenant_id")
        
        self._session.add(product)
        self._session.commit()
        self._session.refresh(product)
        return product
```

**In-Memory Adapter (Same Filtering Logic):**

```python
# adapters/in_memory_product_repository.py
class InMemoryProductRepository(IProductRepository):
    def __init__(self):
        self._products: dict[str, Product] = {}
    
    def list_by_tenant(self, tenant_id: str) -> list[Product]:
        """Filters in-memory products by tenant."""
        return [p for p in self._products.values() if p.tenant_id == tenant_id]
    
    def get_by_id(self, product_id: str, tenant_id: str) -> Product | None:
        """Returns product only if it belongs to tenant."""
        product = self._products.get(product_id)
        if product and product.tenant_id == tenant_id:
            return product
        return None
    
    def create(self, product: Product) -> Product:
        if not product.tenant_id:
            raise ValueError("Product must have a tenant_id")
        
        self._products[product.id] = product
        return product
```

---

## 4. Data Model Requirements

All tenant-scoped entities MUST include a `tenant_id` field.

```python
# models/product.py
from sqlmodel import SQLModel, Field
from typing import Optional

class Product(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, nullable=False)  # REQUIRED
    name: str
    price: float
    stock_quantity: int
```

**Database Index:** Always add an index on `tenant_id` for query performance.

**Foreign Keys:** When referencing other entities, ensure they belong to the same tenant:

```python
class Order(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True)
    tenant_id: str = Field(index=True, nullable=False)
    user_id: str  # User must belong to same tenant
    
    # In service logic, validate:
    # user = user_repo.get_by_id(user_id, tenant_id)
    # if not user:
    #     raise ValueError("User not found in tenant")
```

---

## 5. Testing Tenant Isolation

Write tests that prove tenant isolation works correctly.

### Test 1: Repository Cannot Return Wrong Tenant's Data

```python
# tests/test_tenant_isolation.py
import pytest
from app.adapters.in_memory_product_repository import InMemoryProductRepository
from app.models import Product

def test_list_by_tenant_returns_only_tenant_products():
    # Arrange
    repo = InMemoryProductRepository()
    
    product_tenant1 = Product(id="1", name="Laptop", tenant_id="tenant-1", price=999)
    product_tenant2 = Product(id="2", name="Mouse", tenant_id="tenant-2", price=29)
    
    repo.create(product_tenant1)
    repo.create(product_tenant2)
    
    # Act
    tenant1_products = repo.list_by_tenant("tenant-1")
    
    # Assert
    assert len(tenant1_products) == 1
    assert tenant1_products[0].id == "1"
    assert tenant1_products[0].tenant_id == "tenant-1"

def test_get_by_id_returns_none_for_wrong_tenant():
    # Arrange
    repo = InMemoryProductRepository()
    
    product = Product(id="1", name="Laptop", tenant_id="tenant-1", price=999)
    repo.create(product)
    
    # Act
    result = repo.get_by_id("1", "tenant-2")  # Wrong tenant
    
    # Assert
    assert result is None  # Must not return tenant-1's product
```

### Test 2: Service Enforces Tenant Isolation

```python
def test_service_cannot_create_order_with_wrong_tenant_product():
    # Arrange
    product_repo = InMemoryProductRepository()
    order_repo = InMemoryOrderRepository()
    service = OrderService(order_repo, product_repo)
    
    # Tenant 1 creates a product
    product = Product(id="1", name="Laptop", tenant_id="tenant-1", price=999, stock_quantity=10)
    product_repo.create(product)
    
    # Act & Assert
    # Tenant 2 tries to order Tenant 1's product
    with pytest.raises(ProductNotFoundError):
        service.create_order(
            tenant_id="tenant-2",  # Different tenant
            user_id="user-2",
            items=[OrderItem(product_id="1", quantity=1)]
        )
```

---

## 6. Common Pitfalls

### ❌ Pitfall 1: Filtering in Service Logic

**Wrong:**
```python
class ProductService:
    def list_products(self, tenant_id: str) -> list[Product]:
        all_products = self._product_repo.list_all()  # Gets ALL products
        return [p for p in all_products if p.tenant_id == tenant_id]  # Filter here
```

**Why it's wrong:** If you forget the filter in one place, data leaks across tenants.

**Correct:** Repository handles filtering automatically:
```python
class ProductService:
    def list_products(self, tenant_id: str) -> list[Product]:
        return self._product_repo.list_by_tenant(tenant_id)  # Repository filters
```

### ❌ Pitfall 2: Not Validating Tenant ID

**Wrong:**
```python
@router.get("/products/{product_id}")
def get_product(product_id: str):
    # No tenant validation!
    return product_service.get_product(product_id)
```

**Correct:**
```python
@router.get("/products/{product_id}")
def get_product(
    product_id: str,
    tenant_id: str = Depends(get_current_tenant_id)
):
    return product_service.get_product(product_id, tenant_id)
```

### ❌ Pitfall 3: Forgetting tenant_id in Database Queries

**Wrong:**
```python
statement = select(Product).where(Product.id == product_id)
# Missing tenant_id check!
```

**Correct:**
```python
statement = select(Product).where(
    Product.id == product_id,
    Product.tenant_id == tenant_id  # Always include tenant filter
)
```

---

## 7. Tenant Management

### Creating Tenants

Tenant creation is typically done through:
1. Admin interface
2. Self-service registration
3. API endpoint (protected)

```python
# services/tenant_service.py
class TenantService:
    def __init__(self, tenant_repo: ITenantRepository):
        self._tenant_repo = tenant_repo
    
    def create_tenant(self, name: str, admin_email: str) -> Tenant:
        """Create a new tenant with initial admin user."""
        tenant = Tenant(name=name)
        created_tenant = self._tenant_repo.create(tenant)
        
        # Create admin user for this tenant
        admin_user = User(
            email=admin_email,
            tenant_id=created_tenant.id,
            role="admin"
        )
        self._user_repo.create(admin_user)
        
        return created_tenant
```

### Deactivating Tenants

```python
def deactivate_tenant(self, tenant_id: str) -> Tenant:
    """Deactivate a tenant (soft delete)."""
    tenant = self._tenant_repo.get_by_id(tenant_id)
    if not tenant:
        raise TenantNotFoundError()
    
    tenant.is_active = False
    return self._tenant_repo.update(tenant)
```

**Middleware Check:**
```python
def get_current_tenant_id(request: Request) -> str:
    tenant_id = extract_tenant_id(request)
    
    # Verify tenant is active
    tenant = tenant_service.get_tenant(tenant_id)
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=403, detail="Tenant is inactive")
    
    return tenant_id
```

---

## 8. Performance Considerations

### Database Indexes

Always create indexes on `tenant_id` for all tables:

```sql
CREATE INDEX idx_products_tenant_id ON products(tenant_id);
CREATE INDEX idx_orders_tenant_id ON orders(tenant_id);
CREATE INDEX idx_users_tenant_id ON users(tenant_id);
```

### Composite Indexes

For frequent queries, create composite indexes:

```sql
-- For queries filtering by tenant_id + status
CREATE INDEX idx_orders_tenant_status ON orders(tenant_id, status);

-- For queries filtering by tenant_id + created_at
CREATE INDEX idx_orders_tenant_created ON orders(tenant_id, created_at DESC);
```

### Query Optimization

Use `EXPLAIN ANALYZE` to verify queries are using tenant indexes:

```sql
EXPLAIN ANALYZE
SELECT * FROM products WHERE tenant_id = 'tenant-1' AND category = 'electronics';
```

---

## 9. Checklist

When implementing a multi-tenant feature:

- [ ] All entities include `tenant_id` field
- [ ] Database indexes created on `tenant_id`
- [ ] Port interface requires `tenant_id` parameter
- [ ] All adapters enforce tenant filtering
- [ ] Services accept and pass `tenant_id`
- [ ] API endpoints extract `tenant_id` via dependency
- [ ] Tests prove Tenant A cannot access Tenant B's data
- [ ] Foreign key relationships validated for same tenant
- [ ] Tenant activation status checked in middleware
- [ ] Error messages don't leak tenant information

---

*This guide ensures strict data isolation in multi-tenant applications. Follow these patterns consistently to prevent data leaks.*
