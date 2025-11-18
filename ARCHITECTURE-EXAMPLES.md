# Architecture Examples & Patterns

This document provides complete, copy-pasteable code examples for common patterns. Use these as reference implementations.

---

## 1. Complete Four-Step Pattern Example

This shows the full implementation of a feature using Hexagonal Architecture.

### Example: Product Management System

#### Step 1: Define the Port

```python
# ports/product_repository.py
import abc
from typing import Optional
from app.models import Product

class IProductRepository(abc.ABC):
    """
    Port: Abstract contract for product data persistence.
    
    All implementations must provide these methods with the exact same signature.
    This enables swapping between PostgreSQL, MongoDB, in-memory, etc.
    """
    
    @abc.abstractmethod
    def create(self, product: Product) -> Product:
        """
        Persist a new product.
        
        Args:
            product: Product entity to create
            
        Returns:
            Created product with generated ID
            
        Raises:
            DuplicateProductError: If product with same SKU exists
        """
        pass

    @abc.abstractmethod
    def get_by_id(self, product_id: str) -> Optional[Product]:
        """
        Retrieve a product by its ID.
        
        Args:
            product_id: Unique product identifier
            
        Returns:
            Product if found, None otherwise
        """
        pass
    
    @abc.abstractmethod
    def list_all(self, skip: int = 0, limit: int = 100) -> list[Product]:
        """
        List products with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of products
        """
        pass
    
    @abc.abstractmethod
    def update(self, product: Product) -> Product:
        """
        Update an existing product.
        
        Args:
            product: Product with updated fields
            
        Returns:
            Updated product
            
        Raises:
            ProductNotFoundError: If product doesn't exist
        """
        pass
    
    @abc.abstractmethod
    def delete(self, product_id: str) -> bool:
        """
        Delete a product.
        
        Args:
            product_id: ID of product to delete
            
        Returns:
            True if deleted, False if not found
        """
        pass
    
    @abc.abstractmethod
    def search_by_name(self, name: str) -> list[Product]:
        """
        Search products by name (case-insensitive partial match).
        
        Args:
            name: Search term
            
        Returns:
            List of matching products
        """
        pass
```

#### Step 2A: PostgreSQL Adapter

```python
# adapters/postgres_product_repository.py
from sqlmodel import Session, select, or_
from typing import Optional
from app.ports.product_repository import IProductRepository
from app.models import Product
from app.exceptions import DuplicateProductError, ProductNotFoundError

class PostgresProductRepository(IProductRepository):
    """PostgreSQL implementation of product repository."""
    
    def __init__(self, session: Session):
        """
        Initialize with database session.
        
        Args:
            session: SQLModel database session
        """
        self._session = session
    
    def create(self, product: Product) -> Product:
        """Create a new product in PostgreSQL."""
        # Check for duplicate SKU
        existing = self._session.exec(
            select(Product).where(Product.sku == product.sku)
        ).first()
        
        if existing:
            raise DuplicateProductError(f"Product with SKU {product.sku} already exists")
        
        self._session.add(product)
        self._session.commit()
        self._session.refresh(product)
        return product
    
    def get_by_id(self, product_id: str) -> Optional[Product]:
        """Retrieve product by ID from PostgreSQL."""
        statement = select(Product).where(Product.id == product_id)
        return self._session.exec(statement).first()
    
    def list_all(self, skip: int = 0, limit: int = 100) -> list[Product]:
        """List products with pagination."""
        statement = select(Product).offset(skip).limit(limit)
        return list(self._session.exec(statement).all())
    
    def update(self, product: Product) -> Product:
        """Update existing product."""
        existing = self.get_by_id(product.id)
        if not existing:
            raise ProductNotFoundError(f"Product {product.id} not found")
        
        # Update fields
        for key, value in product.dict(exclude_unset=True).items():
            setattr(existing, key, value)
        
        self._session.add(existing)
        self._session.commit()
        self._session.refresh(existing)
        return existing
    
    def delete(self, product_id: str) -> bool:
        """Delete product by ID."""
        product = self.get_by_id(product_id)
        if not product:
            return False
        
        self._session.delete(product)
        self._session.commit()
        return True
    
    def search_by_name(self, name: str) -> list[Product]:
        """Search products by name using ILIKE."""
        statement = select(Product).where(
            Product.name.ilike(f"%{name}%")
        )
        return list(self._session.exec(statement).all())
```

#### Step 2B: In-Memory Adapter

```python
# adapters/in_memory_product_repository.py
from typing import Optional
from app.ports.product_repository import IProductRepository
from app.models import Product
from app.exceptions import DuplicateProductError, ProductNotFoundError
import uuid

class InMemoryProductRepository(IProductRepository):
    """In-memory implementation for testing."""
    
    def __init__(self):
        """Initialize with empty storage."""
        self._products: dict[str, Product] = {}
        self._sku_index: dict[str, str] = {}  # sku -> product_id mapping
    
    def create(self, product: Product) -> Product:
        """Create product in memory."""
        # Check for duplicate SKU
        if product.sku in self._sku_index:
            raise DuplicateProductError(f"Product with SKU {product.sku} already exists")
        
        # Generate ID if not provided
        if not product.id:
            product.id = str(uuid.uuid4())
        
        self._products[product.id] = product
        self._sku_index[product.sku] = product.id
        return product
    
    def get_by_id(self, product_id: str) -> Optional[Product]:
        """Get product by ID."""
        return self._products.get(product_id)
    
    def list_all(self, skip: int = 0, limit: int = 100) -> list[Product]:
        """List products with pagination."""
        all_products = list(self._products.values())
        return all_products[skip:skip + limit]
    
    def update(self, product: Product) -> Product:
        """Update product in memory."""
        if product.id not in self._products:
            raise ProductNotFoundError(f"Product {product.id} not found")
        
        # Update SKU index if SKU changed
        old_product = self._products[product.id]
        if old_product.sku != product.sku:
            del self._sku_index[old_product.sku]
            self._sku_index[product.sku] = product.id
        
        self._products[product.id] = product
        return product
    
    def delete(self, product_id: str) -> bool:
        """Delete product from memory."""
        if product_id not in self._products:
            return False
        
        product = self._products[product_id]
        del self._sku_index[product.sku]
        del self._products[product_id]
        return True
    
    def search_by_name(self, name: str) -> list[Product]:
        """Search products by name (case-insensitive)."""
        search_term = name.lower()
        return [
            p for p in self._products.values()
            if search_term in p.name.lower()
        ]
```

#### Step 3: Service with Business Logic

```python
# services/product_service.py
from typing import Optional
from app.ports.product_repository import IProductRepository
from app.models import Product
from app.exceptions import ProductNotFoundError, InvalidProductDataError

class ProductService:
    """
    Service containing business logic for product management.
    
    This service depends ONLY on the IProductRepository interface,
    never on concrete implementations.
    """
    
    def __init__(self, product_repo: IProductRepository):
        """
        Initialize service with repository.
        
        Args:
            product_repo: Product repository implementation (interface)
        """
        self._product_repo = product_repo
    
    def create_product(
        self,
        name: str,
        sku: str,
        price: float,
        stock_quantity: int,
        description: Optional[str] = None
    ) -> Product:
        """
        Create a new product with validation.
        
        Business Rules:
        - Price must be positive
        - Stock quantity cannot be negative
        - SKU must be unique
        
        Args:
            name: Product name
            sku: Stock keeping unit (unique)
            price: Product price
            stock_quantity: Initial stock
            description: Optional product description
            
        Returns:
            Created product
            
        Raises:
            InvalidProductDataError: If validation fails
            DuplicateProductError: If SKU already exists
        """
        # Business validation
        if price <= 0:
            raise InvalidProductDataError("Price must be positive")
        
        if stock_quantity < 0:
            raise InvalidProductDataError("Stock quantity cannot be negative")
        
        if not name or not name.strip():
            raise InvalidProductDataError("Product name is required")
        
        # Create product
        product = Product(
            name=name.strip(),
            sku=sku.upper(),  # Normalize SKU to uppercase
            price=price,
            stock_quantity=stock_quantity,
            description=description
        )
        
        return self._product_repo.create(product)
    
    def get_product(self, product_id: str) -> Product:
        """
        Retrieve a product by ID.
        
        Args:
            product_id: Product identifier
            
        Returns:
            Product entity
            
        Raises:
            ProductNotFoundError: If product doesn't exist
        """
        product = self._product_repo.get_by_id(product_id)
        if not product:
            raise ProductNotFoundError(f"Product {product_id} not found")
        return product
    
    def list_products(self, page: int = 1, page_size: int = 20) -> list[Product]:
        """
        List products with pagination.
        
        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            
        Returns:
            List of products
        """
        skip = (page - 1) * page_size
        return self._product_repo.list_all(skip=skip, limit=page_size)
    
    def update_stock(self, product_id: str, quantity_change: int) -> Product:
        """
        Update product stock (add or remove).
        
        Business Rules:
        - Stock cannot go negative
        
        Args:
            product_id: Product to update
            quantity_change: Amount to add (positive) or remove (negative)
            
        Returns:
            Updated product
            
        Raises:
            ProductNotFoundError: If product doesn't exist
            InvalidProductDataError: If operation would make stock negative
        """
        product = self.get_product(product_id)
        
        new_stock = product.stock_quantity + quantity_change
        if new_stock < 0:
            raise InvalidProductDataError(
                f"Cannot reduce stock by {abs(quantity_change)}. "
                f"Current stock: {product.stock_quantity}"
            )
        
        product.stock_quantity = new_stock
        return self._product_repo.update(product)
    
    def update_price(self, product_id: str, new_price: float) -> Product:
        """
        Update product price.
        
        Business Rules:
        - Price must be positive
        
        Args:
            product_id: Product to update
            new_price: New price value
            
        Returns:
            Updated product
            
        Raises:
            ProductNotFoundError: If product doesn't exist
            InvalidProductDataError: If price is invalid
        """
        if new_price <= 0:
            raise InvalidProductDataError("Price must be positive")
        
        product = self.get_product(product_id)
        product.price = new_price
        return self._product_repo.update(product)
    
    def search_products(self, search_term: str) -> list[Product]:
        """
        Search products by name.
        
        Args:
            search_term: Text to search for
            
        Returns:
            Matching products
        """
        if not search_term or not search_term.strip():
            return []
        
        return self._product_repo.search_by_name(search_term.strip())
    
    def delete_product(self, product_id: str) -> None:
        """
        Delete a product.
        
        Args:
            product_id: Product to delete
            
        Raises:
            ProductNotFoundError: If product doesn't exist
        """
        if not self._product_repo.delete(product_id):
            raise ProductNotFoundError(f"Product {product_id} not found")
```

#### Step 4: Dependency Injection Setup

```python
# dependencies.py
from functools import lru_cache
from sqlmodel import Session, create_engine
from sqlmodel.pool import StaticPool
from app.config import AppSettings
from app.ports.product_repository import IProductRepository
from app.adapters.postgres_product_repository import PostgresProductRepository
from app.adapters.in_memory_product_repository import InMemoryProductRepository
from app.services.product_service import ProductService

# Singleton settings
@lru_cache()
def get_settings() -> AppSettings:
    """Get application settings (cached)."""
    return AppSettings()

# Database session factory
def get_db_session() -> Session:
    """
    Create database session.
    
    In production, this would use connection pooling.
    """
    settings = get_settings()
    
    if settings.environment == "local":
        # Use in-memory SQLite for local development
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool
        )
    else:
        # Use configured database URL
        engine = create_engine(settings.database_url)
    
    return Session(engine)

# Repository factory
def get_product_repository(
    settings: AppSettings = None,
    session: Session = None
) -> IProductRepository:
    """
    Create product repository based on configuration.
    
    Args:
        settings: App settings (auto-injected)
        session: DB session (auto-injected)
        
    Returns:
        Appropriate repository implementation
    """
    if settings is None:
        settings = get_settings()
    
    # Choose implementation based on environment
    if settings.use_real_database:
        if session is None:
            session = get_db_session()
        return PostgresProductRepository(session)
    else:
        return InMemoryProductRepository()

# Service factory
def get_product_service(
    product_repo: IProductRepository = None
) -> ProductService:
    """
    Create product service with injected dependencies.
    
    Args:
        product_repo: Repository implementation (auto-injected)
        
    Returns:
        Configured product service
    """
    if product_repo is None:
        product_repo = get_product_repository()
    
    return ProductService(product_repo)
```

#### API Layer (FastAPI)

```python
# api/products.py
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional
from app.services.product_service import ProductService
from app.dependencies import get_product_service
from app.exceptions import (
    ProductNotFoundError,
    InvalidProductDataError,
    DuplicateProductError
)

router = APIRouter(prefix="/api/v1/products", tags=["products"])

# Request/Response Models
class ProductCreate(BaseModel):
    """Request model for creating a product."""
    name: str = Field(..., min_length=1, max_length=255)
    sku: str = Field(..., min_length=1, max_length=50)
    price: float = Field(..., gt=0)
    stock_quantity: int = Field(..., ge=0)
    description: Optional[str] = Field(None, max_length=2000)

class ProductResponse(BaseModel):
    """Response model for product data."""
    id: str
    name: str
    sku: str
    price: float
    stock_quantity: int
    description: Optional[str]

class StockUpdate(BaseModel):
    """Request model for updating stock."""
    quantity_change: int

class PriceUpdate(BaseModel):
    """Request model for updating price."""
    new_price: float = Field(..., gt=0)

# Synchronous Endpoints (Immediate Response)

@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_data: ProductCreate,
    product_service: ProductService = Depends(get_product_service)
):
    """
    Create a new product (synchronous).
    
    Returns the created product immediately.
    """
    try:
        product = product_service.create_product(
            name=product_data.name,
            sku=product_data.sku,
            price=product_data.price,
            stock_quantity=product_data.stock_quantity,
            description=product_data.description
        )
        return ProductResponse(**product.dict())
    except InvalidProductDataError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except DuplicateProductError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: str,
    product_service: ProductService = Depends(get_product_service)
):
    """
    Get a product by ID (synchronous).
    
    Returns product details immediately.
    """
    try:
        product = product_service.get_product(product_id)
        return ProductResponse(**product.dict())
    except ProductNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

@router.get("/", response_model=list[ProductResponse])
def list_products(
    page: int = 1,
    page_size: int = 20,
    product_service: ProductService = Depends(get_product_service)
):
    """
    List products with pagination (synchronous).
    
    Returns list of products immediately.
    """
    products = product_service.list_products(page=page, page_size=page_size)
    return [ProductResponse(**p.dict()) for p in products]

@router.get("/search/{search_term}", response_model=list[ProductResponse])
def search_products(
    search_term: str,
    product_service: ProductService = Depends(get_product_service)
):
    """
    Search products by name (synchronous).
    
    Returns matching products immediately.
    """
    products = product_service.search_products(search_term)
    return [ProductResponse(**p.dict()) for p in products]

@router.patch("/{product_id}/stock", response_model=ProductResponse)
def update_stock(
    product_id: str,
    stock_update: StockUpdate,
    product_service: ProductService = Depends(get_product_service)
):
    """
    Update product stock (synchronous).
    
    Returns updated product immediately.
    """
    try:
        product = product_service.update_stock(product_id, stock_update.quantity_change)
        return ProductResponse(**product.dict())
    except ProductNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidProductDataError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.patch("/{product_id}/price", response_model=ProductResponse)
def update_price(
    product_id: str,
    price_update: PriceUpdate,
    product_service: ProductService = Depends(get_product_service)
):
    """
    Update product price (synchronous).
    
    Returns updated product immediately.
    """
    try:
        product = product_service.update_price(product_id, price_update.new_price)
        return ProductResponse(**product.dict())
    except ProductNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except InvalidProductDataError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: str,
    product_service: ProductService = Depends(get_product_service)
):
    """
    Delete a product (synchronous).
    
    Returns 204 No Content on success.
    """
    try:
        product_service.delete_product(product_id)
    except ProductNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
```

---

## 2. Asynchronous Processing Example

This example shows how to handle long-running operations asynchronously.

### Background Task (Using Celery)

```python
# tasks/product_import.py
from celery import shared_task
import logging
from app.dependencies import get_product_service
from app.models import Product

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def import_products_from_csv(self, file_path: str, user_id: str):
    """
    Import products from CSV file (runs in background).
    
    This is idempotent - can be safely retried.
    
    Args:
        file_path: Path to CSV file
        user_id: User who initiated the import
        
    Returns:
        dict with import results
    """
    try:
        product_service = get_product_service()
        imported_count = 0
        failed_count = 0
        errors = []
        
        # Read CSV and process (simplified)
        with open(file_path, 'r') as f:
            # Skip header
            next(f)
            
            for line_num, line in enumerate(f, start=2):
                try:
                    name, sku, price, stock = line.strip().split(',')
                    
                    product_service.create_product(
                        name=name,
                        sku=sku,
                        price=float(price),
                        stock_quantity=int(stock)
                    )
                    imported_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    errors.append(f"Line {line_num}: {str(e)}")
                    logger.warning(f"Failed to import line {line_num}: {e}")
        
        result = {
            "status": "completed",
            "imported": imported_count,
            "failed": failed_count,
            "errors": errors[:10]  # Limit error list
        }
        
        logger.info(f"Import completed: {imported_count} imported, {failed_count} failed")
        return result
        
    except Exception as exc:
        logger.error(f"Import task failed: {exc}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

### Async API Endpoint

```python
# api/products.py (additional endpoint)
from app.tasks.product_import import import_products_from_csv
import uuid

class ImportResponse(BaseModel):
    """Response for async import operation."""
    message: str
    task_id: str
    status_url: str

@router.post("/import", response_model=ImportResponse, status_code=status.HTTP_202_ACCEPTED)
def import_products(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    request: Request
):
    """
    Import products from CSV (asynchronous).
    
    Returns 202 Accepted immediately with task ID.
    Client can poll status endpoint to check progress.
    """
    # Save uploaded file
    file_path = f"/tmp/{uuid.uuid4()}.csv"
    with open(file_path, "wb") as f:
        f.write(file.file.read())
    
    # Queue background task
    task = import_products_from_csv.delay(file_path, user_id="current_user")
    
    # Return immediately
    return ImportResponse(
        message="Import started",
        task_id=task.id,
        status_url=f"{request.base_url}api/v1/products/import/{task.id}/status"
    )

@router.get("/import/{task_id}/status")
def get_import_status(task_id: str):
    """
    Check status of import task.
    
    Returns current task status.
    """
    task = import_products_from_csv.AsyncResult(task_id)
    
    if task.state == "PENDING":
        return {"status": "pending", "message": "Task is waiting to be processed"}
    elif task.state == "PROGRESS":
        return {"status": "in_progress", "progress": task.info.get("progress", 0)}
    elif task.state == "SUCCESS":
        return {"status": "completed", "result": task.result}
    elif task.state == "FAILURE":
        return {"status": "failed", "error": str(task.info)}
    else:
        return {"status": task.state}
```

---

## 3. Complete Testing Examples

### Unit Test (Fast, In-Memory)

```python
# tests/unit/test_product_service.py
import pytest
from app.services.product_service import ProductService
from app.adapters.in_memory_product_repository import InMemoryProductRepository
from app.exceptions import InvalidProductDataError, ProductNotFoundError

class TestProductService:
    """Unit tests for ProductService using in-memory adapter."""
    
    @pytest.fixture
    def product_service(self):
        """Provide a ProductService with in-memory repository."""
        repo = InMemoryProductRepository()
        return ProductService(repo)
    
    def test_create_product_success(self, product_service):
        """Test creating a product with valid data."""
        # Act
        product = product_service.create_product(
            name="Laptop",
            sku="LAP001",
            price=999.99,
            stock_quantity=10
        )
        
        # Assert
        assert product.id is not None
        assert product.name == "Laptop"
        assert product.sku == "LAP001"  # SKU normalized to uppercase
        assert product.price == 999.99
        assert product.stock_quantity == 10
    
    def test_create_product_with_negative_price_fails(self, product_service):
        """Test that negative price is rejected."""
        # Act & Assert
        with pytest.raises(InvalidProductDataError) as exc_info:
            product_service.create_product(
                name="Laptop",
                sku="LAP001",
                price=-100.0,
                stock_quantity=10
            )
        
        assert "Price must be positive" in str(exc_info.value)
    
    def test_update_stock_success(self, product_service):
        """Test updating stock quantity."""
        # Arrange
        product = product_service.create_product(
            name="Mouse",
            sku="MSE001",
            price=29.99,
            stock_quantity=50
        )
        
        # Act
        updated = product_service.update_stock(product.id, -10)
        
        # Assert
        assert updated.stock_quantity == 40
    
    def test_update_stock_cannot_go_negative(self, product_service):
        """Test that stock cannot go below zero."""
        # Arrange
        product = product_service.create_product(
            name="Keyboard",
            sku="KEY001",
            price=79.99,
            stock_quantity=5
        )
        
        # Act & Assert
        with pytest.raises(InvalidProductDataError) as exc_info:
            product_service.update_stock(product.id, -10)
        
        assert "Cannot reduce stock" in str(exc_info.value)
    
    def test_get_nonexistent_product_raises_error(self, product_service):
        """Test that getting nonexistent product raises error."""
        # Act & Assert
        with pytest.raises(ProductNotFoundError):
            product_service.get_product("nonexistent-id")
    
    def test_search_products_case_insensitive(self, product_service):
        """Test product search is case-insensitive."""
        # Arrange
        product_service.create_product("Gaming Laptop", "GAM001", 1500.0, 5)
        product_service.create_product("Office Laptop", "OFF001", 800.0, 10)
        product_service.create_product("Gaming Mouse", "GAM002", 50.0, 20)
        
        # Act
        results = product_service.search_products("LAPTOP")
        
        # Assert
        assert len(results) == 2
        assert all("laptop" in p.name.lower() for p in results)
```

### Integration Test (With Real Database)

```python
# tests/integration/test_product_repository_postgres.py
import pytest
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool
from app.adapters.postgres_product_repository import PostgresProductRepository
from app.models import Product
from app.exceptions import DuplicateProductError

@pytest.fixture
def db_session():
    """Provide a clean database session for each test."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        yield session

@pytest.fixture
def product_repo(db_session):
    """Provide PostgreSQL repository with test database."""
    return PostgresProductRepository(db_session)

def test_create_and_retrieve_product(product_repo):
    """Test creating and retrieving a product from database."""
    # Arrange
    product = Product(
        name="Test Product",
        sku="TST001",
        price=99.99,
        stock_quantity=100
    )
    
    # Act
    created = product_repo.create(product)
    retrieved = product_repo.get_by_id(created.id)
    
    # Assert
    assert retrieved is not None
    assert retrieved.name == "Test Product"
    assert retrieved.sku == "TST001"

def test_duplicate_sku_raises_error(product_repo):
    """Test that duplicate SKU is rejected."""
    # Arrange
    product1 = Product(name="Product 1", sku="DUP001", price=50.0, stock_quantity=10)
    product2 = Product(name="Product 2", sku="DUP001", price=75.0, stock_quantity=20)
    
    # Act
    product_repo.create(product1)
    
    # Assert
    with pytest.raises(DuplicateProductError):
        product_repo.create(product2)
```

---

## 4. Shared Tests - Run Same Tests Against Multiple Adapters

Write repository tests once and run them automatically against both in-memory and PostgreSQL adapters.

### Conftest Setup

```python
# tests/conftest.py
import pytest
from sqlmodel import Session, create_engine, SQLModel

# === In-Memory Fixtures ===
@pytest.fixture
def in_memory_product_repo():
    """Fresh in-memory repository for each test."""
    return InMemoryProductRepository()

# === PostgreSQL Fixtures ===
@pytest.fixture(scope="session")
def test_engine():
    """Database engine for test session."""
    try:
        engine = create_engine(
            "postgresql://postgres:postgres@localhost:5432/test_db",
            echo=False
        )
        SQLModel.metadata.create_all(engine)
        yield engine
        SQLModel.metadata.drop_all(engine)
        engine.dispose()
    except Exception:
        pytest.skip("PostgreSQL not available")

@pytest.fixture
def db_session(test_engine):
    """Fresh database session with transaction rollback."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()  # Rollback after each test
    connection.close()

@pytest.fixture
def postgres_product_repo(db_session):
    """PostgreSQL repository with database session."""
    return PostgresProductRepository(db_session)

# === Parametrized Fixture (The Magic!) ===
@pytest.fixture(
    params=["in_memory", "postgres"],
    ids=["InMemory", "PostgreSQL"]
)
def product_repo(request, in_memory_product_repo):
    """Parametrized fixture that provides BOTH adapters.

    Tests using this fixture run twice automatically:
    - Once with InMemoryProductRepository
    - Once with PostgresProductRepository
    """
    if request.param == "in_memory":
        return in_memory_product_repo
    elif request.param == "postgres":
        try:
            # Lazy load PostgreSQL to allow graceful skip
            return request.getfixturevalue("postgres_product_repo")
        except Exception:
            pytest.skip("PostgreSQL not available")
```

### Shared Test Examples

```python
# tests/shared/test_product_repository.py
from app.models import Product
from app.ports import IProductRepository
from app.exceptions import DuplicateProductError

def test_create_product(product_repo: IProductRepository):
    """Test creating a product - runs with BOTH adapters."""
    # Arrange
    product = Product(
        name="Laptop",
        sku="LAP001",
        price=999.99,
        stock_quantity=10
    )

    # Act
    created = product_repo.create(product)

    # Assert
    assert created.id is not None
    assert created.name == "Laptop"
    assert created.sku == "LAP001"

def test_get_by_id(product_repo: IProductRepository):
    """Test retrieving product by ID - runs with BOTH adapters."""
    # Arrange
    product = Product(name="Mouse", sku="MSE001", price=29.99, stock_quantity=50)
    created = product_repo.create(product)

    # Act
    retrieved = product_repo.get_by_id(created.id)

    # Assert
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.name == "Mouse"

def test_duplicate_sku_fails(product_repo: IProductRepository):
    """Test that duplicate SKU is rejected - runs with BOTH adapters."""
    # Arrange
    product1 = Product(name="Product 1", sku="DUP001", price=50, stock_quantity=10)
    product_repo.create(product1)

    # Act & Assert
    product2 = Product(name="Product 2", sku="DUP001", price=75, stock_quantity=20)
    with pytest.raises(DuplicateProductError):
        product_repo.create(product2)

def test_update_product(product_repo: IProductRepository):
    """Test updating a product - runs with BOTH adapters."""
    # Arrange
    product = Product(name="Keyboard", sku="KEY001", price=79.99, stock_quantity=25)
    created = product_repo.create(product)

    # Act
    created.price = 69.99
    updated = product_repo.update(created)

    # Assert
    assert updated.price == 69.99

    # Verify persistence
    retrieved = product_repo.get_by_id(created.id)
    assert retrieved.price == 69.99

def test_delete_product(product_repo: IProductRepository):
    """Test deleting a product - runs with BOTH adapters."""
    # Arrange
    product = Product(name="Monitor", sku="MON001", price=299, stock_quantity=15)
    created = product_repo.create(product)

    # Act
    deleted = product_repo.delete(created.id)

    # Assert
    assert deleted is True

    # Verify deletion
    retrieved = product_repo.get_by_id(created.id)
    assert retrieved is None
```

### Running Shared Tests

```bash
# Run all shared tests with both adapters
pytest tests/shared/test_product_repository.py -v

# Output:
# test_create_product[InMemory] PASSED
# test_create_product[PostgreSQL] PASSED
# test_get_by_id[InMemory] PASSED
# test_get_by_id[PostgreSQL] PASSED
# test_duplicate_sku_fails[InMemory] PASSED
# test_duplicate_sku_fails[PostgreSQL] PASSED
# test_update_product[InMemory] PASSED
# test_update_product[PostgreSQL] PASSED
# test_delete_product[InMemory] PASSED
# test_delete_product[PostgreSQL] PASSED
#
# Result: 5 test functions × 2 adapters = 10 test executions

# Run only in-memory tests (fast, no database needed)
pytest tests/shared/ -k "InMemory" -v

# Run only PostgreSQL tests (requires database)
pytest tests/shared/ -k "PostgreSQL" -v

# Run specific test with both adapters
pytest tests/shared/test_product_repository.py::test_create_product -v
```

### When to Use Shared Tests

**Use shared tests for:**
- Repository CRUD operations
- Business validation rules that apply to all adapters
- Any test that verifies the port contract

**Don't use shared tests for:**
- Adapter-specific features (database constraints, transactions)
- Performance benchmarks
- Service layer tests (use regular unit tests)

### Result

Write repository tests once, verify with both adapters automatically. This ensures:
- Adapters truly implement the port contract identically
- No code duplication between unit and integration tests
- Easy to add new adapters (just update parametrized fixture)

---

*Use these examples as templates for implementing new features following the same patterns.*
