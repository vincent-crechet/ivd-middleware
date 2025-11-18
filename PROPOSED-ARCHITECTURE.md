# Proposed Architecture: IVD Middleware Decomposition

This document proposes the decomposition of the IVD Middleware application into services and web apps based on the SPECIFICATION.md and ARCHITECTURE*.md documents.

---

## Architecture Overview

The system is decomposed into **3 core backend services** organized by domain boundaries, **2 web applications** for different user types, and an optional API Gateway for routing and authentication.

---

## Backend Services

### 1. Platform Service (Identity & Multi-Tenancy)

**Responsibility:** Tenant management, user management, authentication, authorization

**Key Features:**
- Create/manage tenants with data isolation
- User CRUD operations (Admin, Technician, Pathologist roles)
- Authentication (JWT token generation with `tenant_id` embedded)
- Authorization and role-based access control
- Tenant activation/deactivation

**Ports/Adapters:**
- `ITenantRepository` → PostgreSQL adapter, In-memory adapter
- `IUserRepository` → PostgreSQL adapter, In-memory adapter
- `IAuthenticationService` → JWT adapter, Mock adapter
- `IPasswordHasher` → Bcrypt adapter

**API Endpoints:**
- `POST /api/v1/tenants` - Create tenant with first admin user
- `GET/PUT/DELETE /api/v1/tenants/{id}`
- `POST /api/v1/auth/login` - Returns JWT with tenant_id
- `POST /api/v1/auth/refresh`
- `GET/POST/PUT/DELETE /api/v1/users`

**Why separate?**
- Clear security boundary
- Can be scaled independently
- Reusable across multiple applications
- Authentication/authorization is cross-cutting

---

### 2. Laboratory Integration Service (LIS Adapter & Ingestion)

**Responsibility:** Connect to external LIS systems, ingest samples and results

**Key Features:**
- LIS connection configuration per tenant
- Push model: Expose API endpoints to receive incoming orders from LIS
- Pull model: Periodically retrieve data from LIS
- Multiple LIS adapters (Mock, File Upload, REST API)
- Duplicate detection
- Sample and result data normalization

**Ports/Adapters:**
- `ILISAdapter` → MockLISAdapter, FileUploadAdapter, RESTAPIAdapter (push), RESTAPIAdapter (pull)
- `ISampleRepository` → PostgreSQL adapter, In-memory adapter
- `IResultRepository` → PostgreSQL adapter, In-memory adapter
- `ILISConfigRepository` → PostgreSQL adapter (stores LIS connection settings per tenant)
- `ITaskQueue` → Celery/RabbitMQ adapter (for pull model scheduling), In-memory adapter

**API Endpoints:**
- `POST /api/v1/lis/config` - Configure LIS connection for tenant
- `POST /api/v1/lis/ingest` - **Push model endpoint** (receives orders from external LIS)
- `POST /api/v1/lis/manual-upload` - File upload adapter
- `GET /api/v1/lis/connection-status` - Test LIS connection health
- `GET /api/v1/samples` - Query samples for tenant
- `GET /api/v1/samples/{id}/results` - Get results for a sample

**Why separate?**
- LIS integration is complex and independent from verification logic
- Different scaling requirements (ingestion can be bursty)
- Can swap LIS adapters without touching verification
- Background jobs for pull model are isolated

---

### 3. Verification & Review Service (Core Business Logic)

**Responsibility:** Auto-verification, manual review workflow, verification rules configuration

**Key Features:**
- Auto-verification rules (Reference Range, Critical Range, Instrument Flag, Delta Check)
- Auto-verification settings configuration per tenant
- Manual review workflow (sample-level reviews)
- Review queue management
- Escalation workflow
- Patient history for delta checks

**Ports/Adapters:**
- `ISampleRepository` → PostgreSQL adapter, In-memory adapter (shared with Integration Service)
- `IResultRepository` → PostgreSQL adapter, In-memory adapter (shared)
- `IReviewRepository` → PostgreSQL adapter, In-memory adapter
- `IAutoVerificationSettingsRepository` → PostgreSQL adapter, In-memory adapter
- `IVerificationEngine` → Rule-based verification adapter
- `INotificationService` → Email adapter (future), Mock adapter

**API Endpoints:**
- `POST /api/v1/verification/settings` - Configure auto-verification settings (ranges, flags)
- `GET /api/v1/verification/settings` - Get settings for tenant
- `GET /api/v1/reviews/queue` - Get review queue for authenticated user
- `POST /api/v1/reviews` - Create/update review
- `POST /api/v1/reviews/{id}/approve` - Approve sample
- `POST /api/v1/reviews/{id}/reject` - Reject sample
- `POST /api/v1/reviews/{id}/escalate` - Escalate to pathologist
- `GET /api/v1/samples/{id}` - Get sample with verification status
- `GET /api/v1/results/{id}/history` - Get patient history for delta checks

**Why separate?**
- Core business domain logic
- Complex verification rules isolated
- Can iterate on verification algorithms independently
- Different access patterns than ingestion

---

## Service Communication Pattern

Since services need to share data (especially samples/results), two approaches are considered:

### Option A: Shared Database (Recommended for MVP)
- All services connect to same PostgreSQL database
- Each service only accesses its own tables + shared tables (samples, results)
- Enforced via repository interfaces and multi-tenant filtering
- Simpler for MVP, easier transactions

### Option B: Event-Driven (More scalable)
- Integration Service publishes `SampleIngested` events
- Verification Service subscribes and triggers auto-verification
- Requires message broker (RabbitMQ, Kafka)
- Better for scaling, but more complex

**Recommendation for MVP:** Start with **Option A** (shared database), migrate to **Option B** in Phase 2.

---

## Frontend Web Applications

### 1. Laboratory Portal (Main SPA)

**Technology:** React/Vue/Angular SPA

**User Roles:** All users (Admin, Technician, Pathologist)

**Features by Role:**

**Admin Views:**
- Tenant configuration dashboard
- User management (create, assign roles)
- LIS connection configuration
- Auto-verification settings (configure ranges, critical thresholds, flags)
- System health monitoring
- Audit logs

**Technician Views:**
- Review queue (samples needing manual review)
- Sample search and filtering
- Result details with flagged reasons
- Approve/reject workflow
- Patient history view

**Pathologist Views:**
- Escalated review queue
- All samples and results
- Detailed review with clinical comments
- Approve/reject escalated cases

**Why single app?**
- Shared UI components (sample viewer, result table)
- Single authentication flow
- Easier to maintain
- Role-based routing handles different views
- All users work with same data model

---

### 2. System Admin Portal (Optional - for Platform Operators)

**Technology:** Simple React/Vue SPA

**User Role:** System operators (not laboratory users)

**Features:**
- Create new laboratory tenants
- View all tenants
- Monitor system health across tenants
- Deactivate tenants
- Generate tenant API keys

**Why separate?**
- Different user base (platform operators vs. laboratory staff)
- Different security requirements
- Can be deployed separately
- Not needed for MVP (can be API-only initially)

---

## API Gateway / BFF Pattern

**Recommendation:** Use **API Gateway** pattern for frontend-backend communication

**API Gateway Service** (Lightweight)
- Single entry point for web apps
- Routes requests to appropriate backend services
- Handles authentication (validates JWT, extracts tenant_id)
- Aggregates responses from multiple services if needed
- CORS handling

**Endpoints:**
```
/api/v1/platform/*     → Platform Service
/api/v1/lis/*          → Laboratory Integration Service
/api/v1/verification/* → Verification & Review Service
/api/v1/samples/*      → Query both Integration + Verification Services
```

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Load Balancer                        │
└─────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼────────┐ ┌──────▼───────┐ ┌────────▼────────┐
│ Laboratory     │ │ Admin Portal │ │   API Gateway   │
│ Portal (SPA)   │ │    (SPA)     │ │   (Lightweight) │
└────────────────┘ └──────────────┘ └─────────┬───────┘
                                              │
                    ┌─────────────────────────┼─────────────────────┐
                    │                         │                     │
           ┌────────▼─────────┐    ┌─────────▼────────┐  ┌────────▼──────────┐
           │ Platform Service │    │ LIS Integration  │  │ Verification &    │
           │ (FastAPI)        │    │ Service (FastAPI)│  │ Review Service    │
           │                  │    │                  │  │ (FastAPI)         │
           └────────┬─────────┘    └─────────┬────────┘  └─────────┬─────────┘
                    │                        │                     │
                    │                        │                     │
                    └────────────────────────┼─────────────────────┘
                                             │
                                  ┌──────────▼──────────┐
                                  │  PostgreSQL         │
                                  │  (Shared Database)  │
                                  │  Multi-tenant       │
                                  └─────────────────────┘
                                             │
                                  ┌──────────▼──────────┐
                                  │  RabbitMQ/Celery    │
                                  │  (Background tasks) │
                                  └─────────────────────┘
```

---

## Folder Structure (Monorepo Recommended for MVP)

```
ivd_middleware/
├── services/
│   ├── platform/              # Platform Service
│   │   ├── app/
│   │   │   ├── models/
│   │   │   ├── ports/
│   │   │   ├── adapters/
│   │   │   ├── services/
│   │   │   ├── api/
│   │   │   ├── exceptions/
│   │   │   ├── config.py
│   │   │   ├── dependencies.py
│   │   │   └── main.py
│   │   ├── tests/
│   │   │   ├── conftest.py
│   │   │   ├── unit/
│   │   │   ├── integration/
│   │   │   └── shared/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── lis_integration/       # LIS Integration Service
│   │   ├── app/
│   │   │   ├── models/
│   │   │   ├── ports/
│   │   │   ├── adapters/
│   │   │   │   ├── lis_adapters/  # Mock, File, REST adapters
│   │   │   │   ├── postgres_*.py
│   │   │   │   └── in_memory_*.py
│   │   │   ├── services/
│   │   │   ├── api/
│   │   │   ├── tasks/            # Background pull jobs
│   │   │   ├── exceptions/
│   │   │   ├── config.py
│   │   │   ├── dependencies.py
│   │   │   └── main.py
│   │   ├── tests/
│   │   │   ├── conftest.py
│   │   │   ├── unit/
│   │   │   ├── integration/
│   │   │   └── shared/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── verification/          # Verification & Review Service
│   │   ├── app/
│   │   │   ├── models/
│   │   │   ├── ports/
│   │   │   ├── adapters/
│   │   │   │   ├── verification_engine/
│   │   │   │   ├── postgres_*.py
│   │   │   │   └── in_memory_*.py
│   │   │   ├── services/
│   │   │   ├── api/
│   │   │   ├── exceptions/
│   │   │   ├── config.py
│   │   │   ├── dependencies.py
│   │   │   └── main.py
│   │   ├── tests/
│   │   │   ├── conftest.py
│   │   │   ├── unit/
│   │   │   ├── integration/
│   │   │   └── shared/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   └── api_gateway/           # API Gateway (Optional for MVP)
│       ├── app/
│       │   └── main.py
│       ├── Dockerfile
│       └── requirements.txt
│
├── web_apps/
│   ├── laboratory_portal/     # Main SPA for all lab users
│   │   ├── src/
│   │   │   ├── components/
│   │   │   ├── views/
│   │   │   │   ├── admin/
│   │   │   │   ├── technician/
│   │   │   │   └── pathologist/
│   │   │   ├── services/      # API clients
│   │   │   ├── router/        # Role-based routing
│   │   │   └── App.vue
│   │   ├── Dockerfile
│   │   └── package.json
│   │
│   └── system_admin_portal/   # System operator portal
│       ├── src/
│       ├── Dockerfile
│       └── package.json
│
├── shared/                    # Shared code (if needed)
│   └── models/                # Shared domain models
│
├── docker-compose.yml
├── docker-compose.test.yml
├── SPECIFICATION.md
├── ARCHITECTURE-CORE.md
├── ARCHITECTURE-MULTITENANCY.md
├── PROPOSED-ARCHITECTURE.md
└── README.md
```

---

## Data Model Ownership

### Platform Service owns:
- `tenants` table
- `users` table
- Authentication tokens (in-memory or Redis)

### LIS Integration Service owns:
- `lis_configurations` table
- `samples` table (created here)
- `results` table (created here)
- `lis_sync_status` table

### Verification Service owns:
- `auto_verification_settings` table
- `reviews` table
- `review_decisions` table

### Shared (read by multiple services):
- `samples` table (created by Integration, read by Verification)
- `results` table (created by Integration, updated by Verification with verification status)

---

## Key Architectural Decisions

### 1. Multi-tenancy enforced at repository level
(per ARCHITECTURE-MULTITENANCY.md)
- All repositories filter by `tenant_id`
- JWT tokens contain `tenant_id`
- API Gateway extracts and validates tenant context
- Every entity includes `tenant_id` field with database index

### 2. Hexagonal Architecture in each service
(per ARCHITECTURE-CORE.md)
- Services depend only on Ports (interfaces)
- Minimum 2 adapters per port (PostgreSQL + In-memory)
- Shared tests run against all adapters
- Business logic completely isolated from infrastructure

### 3. Synchronous communication for MVP
- Services share PostgreSQL database
- Direct SQL queries with proper tenant filtering
- Can migrate to event-driven later
- Simpler transactions and debugging

### 4. Push + Pull LIS integration
- Push: LIS calls Integration Service API endpoint
- Pull: Background Celery tasks poll LIS APIs
- Both trigger auto-verification in Verification Service
- Tenant-specific API keys for push authentication

### 5. Sample-level reviews
- Reviews cover entire samples, not individual results
- Reviewers see all results (auto-verified and flagged) for context
- Flagged results clearly marked with reason
- Approved/rejected status tracked per result within review

### 6. Verification happens in Verification Service
- Integration Service only ingests raw data
- Verification Service subscribes to new samples (or polls)
- Auto-verification rules applied immediately
- Results marked as "verified" or "needs_review"

---

## Implementation Phases

### Phase 1: MVP (P0 Features)
1. **Platform Service**
   - Tenant creation with first admin user
   - User authentication (JWT)
   - Role-based access control

2. **LIS Integration Service**
   - Mock LIS adapter
   - Push model API endpoint for receiving orders
   - Sample and result ingestion
   - Duplicate detection

3. **Verification Service**
   - Auto-verification settings configuration
   - All four verification rules (Reference Range, Critical Range, Instrument Flag, Delta Check)
   - Manual review workflow (approve/reject at sample level)
   - Review queue

4. **Laboratory Portal**
   - Admin views (tenant config, user management, verification settings)
   - Technician views (review queue, sample search)
   - Basic authentication and routing

### Phase 2: Enhanced Features (P1)
- File upload LIS adapter
- REST API pull model
- Review escalation workflow
- Patient history view in review screen
- LIS connection testing and health monitoring
- System Admin Portal

### Phase 3: Advanced Features (P2+)
- Advanced search and filtering
- Bulk operations
- Custom verification rules
- Email notifications
- Analytics and reporting
- Migration to event-driven architecture

---

## Technology Stack (Recommended)

### Backend Services
- **Framework:** FastAPI (Python)
- **Database:** PostgreSQL with SQLModel ORM
- **Background Tasks:** Celery + RabbitMQ
- **Authentication:** JWT tokens
- **Testing:** pytest with parametrized fixtures

### Frontend
- **Framework:** Vue.js 3 or React
- **State Management:** Pinia (Vue) or Redux (React)
- **UI Components:** Vuetify/PrimeVue or Material-UI/Ant Design
- **API Client:** Axios
- **Routing:** Vue Router / React Router with role guards

### Infrastructure
- **Container:** Docker
- **Orchestration:** Docker Compose (dev), Kubernetes (production)
- **API Gateway:** Nginx or Traefik
- **Monitoring:** Prometheus + Grafana (future)

---

## Benefits of This Architecture

### Separation of Concerns
- Each service has a clear, focused responsibility
- Changes to one service don't affect others
- Different teams can work on different services

### Scalability
- Services can be scaled independently based on load
- LIS Integration can handle bursty ingestion traffic
- Verification can scale for computation-heavy rule evaluation

### Testability
- Hexagonal architecture enables fast unit tests with in-memory adapters
- Integration tests verify real database behavior
- Shared tests ensure adapter consistency

### Maintainability
- Clear boundaries reduce cognitive load
- New features added to appropriate service
- Technology changes isolated to specific adapters

### Multi-tenancy
- Data isolation enforced at repository level
- Tenant context propagated through all layers
- No risk of cross-tenant data leakage

### Flexibility
- Easy to add new LIS adapters
- Verification rules can evolve independently
- Can migrate to microservices/event-driven later

---

## Summary

**3 Backend Services:**
1. **Platform Service** - Identity, tenants, users, auth
2. **LIS Integration Service** - LIS adapters, ingestion, samples/results
3. **Verification & Review Service** - Auto-verification, manual review, rules

**2 Web Apps:**
1. **Laboratory Portal** - Main SPA for all laboratory users (role-based views)
2. **System Admin Portal** - Optional, for platform operators

**1 Optional API Gateway** - Single entry point, auth validation, routing

This decomposition:
- ✅ Follows Hexagonal Architecture principles (ARCHITECTURE-CORE.md)
- ✅ Enforces multi-tenancy at all layers (ARCHITECTURE-MULTITENANCY.md)
- ✅ Clear service boundaries based on domain (SPECIFICATION.md features)
- ✅ Independently testable and deployable
- ✅ Simple enough for MVP
- ✅ Scales for future growth
- ✅ Supports both push and pull LIS integration models
- ✅ Complete audit trail for regulatory compliance

---

*This architecture proposal serves as the blueprint for implementing the IVD Middleware system. Review and adjust as needed before proceeding with implementation.*
