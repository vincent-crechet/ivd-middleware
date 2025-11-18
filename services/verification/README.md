# Verification & Review Service

Auto-verification and manual review service for IVD Middleware.

**📋 Specification:** See [SPECIFICATION-VERIFICATION.md](../../SPECIFICATION-VERIFICATION.md) for detailed requirements, acceptance criteria, and business rules.

## Responsibility

- Auto-verification rules (Reference Range, Critical Range, Instrument Flag, Delta Check)
- Auto-verification settings configuration per tenant
- Manual review workflow (sample-level reviews)
- Review queue management
- Escalation workflow

## API Endpoints

### Verification Settings
- `POST /api/v1/verification/settings` - Configure auto-verification settings
- `GET /api/v1/verification/settings` - Get settings for tenant

### Reviews
- `GET /api/v1/reviews/queue` - Get review queue
- `POST /api/v1/reviews` - Create/update review
- `POST /api/v1/reviews/{id}/approve` - Approve sample
- `POST /api/v1/reviews/{id}/reject` - Reject sample
- `POST /api/v1/reviews/{id}/escalate` - Escalate to pathologist

### Samples & Results
- `GET /api/v1/samples/{id}` - Get sample with verification status
- `GET /api/v1/results/{id}/history` - Get patient history for delta checks

## Running

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8002
pytest
```

## Architecture

Follows Hexagonal Architecture with multi-tenant support.
