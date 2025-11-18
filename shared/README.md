# Shared Components

This directory contains code and models shared across multiple services.

## Structure

- `models/` - Shared domain models that multiple services need to access

## Usage

Services can import shared models to ensure consistency:

```python
from shared.models import SomeSharedModel
```

## Guidelines

- Only place truly shared code here
- Keep services as independent as possible
- Consider if code can stay within a single service before making it shared
- Document dependencies clearly
