# Shared Components

This directory contains code and models shared across multiple services.

## Structure

- `models/` - Shared domain models that multiple services need to access

## Usage

Services can import shared models to ensure consistency:

```python
from shared.models import Order, OrderStatus, OrderPriority
```

## Shared Models

### Order Model

The `Order` model is the canonical representation of test orders and is shared between:
- **LIS Integration** - Creates orders from external LIS systems (owner)
- **Instrument Integration** - Assigns orders to instruments and tracks execution

```python
from shared.models import Order, OrderStatus, OrderPriority

# Create an order
order = Order(
    tenant_id="tenant-123",
    sample_id="sample-456",
    external_lis_order_id="LIS-ORDER-001",
    patient_id="PAT-789",
    test_codes='["GLU", "CBC"]',  # JSON array
    priority=OrderPriority.ROUTINE,
    status=OrderStatus.PENDING
)
```

## Data Flow Architecture

### Order Flow
```
External LIS → LIS Integration (creates Order) → Instrument Integration (assigns to instrument)
```

### Result Flow
```
Instrument → InstrumentResult → Verification → Result → External LIS
             (raw data)         (rules check)  (verified)
```

### Model Ownership

| Model | Owner Service | Other Services |
|-------|--------------|----------------|
| Order | LIS Integration | Instrument Integration (read/update) |
| Sample | LIS Integration | - |
| Result | LIS Integration | Verification (reference) |
| InstrumentResult | Instrument Integration | Verification (reference) |
| Instrument | Instrument Integration | - |

### Database Tables

All services share the same PostgreSQL database:

| Table | Service | Description |
|-------|---------|-------------|
| `orders` | Shared | Test orders from LIS |
| `samples` | LIS Integration | Patient samples |
| `results` | LIS Integration | Verified results for LIS upload |
| `instrument_results` | Instrument Integration | Raw results from instruments |
| `instruments` | Instrument Integration | Instrument configurations |

## Guidelines

- Only place truly shared code here
- Keep services as independent as possible
- Consider if code can stay within a single service before making it shared
- Document dependencies clearly
- FK constraints are omitted for cross-service references (logical references maintained by business logic)
