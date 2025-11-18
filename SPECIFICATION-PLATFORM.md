# Platform Service - Specification

*Part of IVD Middleware. See [SPECIFICATION.md](SPECIFICATION.md) for system overview, cross-cutting concerns, and global non-functional requirements.*

---

## Service Responsibility

The Platform Service is the identity and multi-tenancy foundation of the IVD Middleware system. It manages:

- **Tenant Management**: Laboratory organization setup and configuration
- **User Management**: User accounts with role-based access control
- **Authentication**: Secure login with JWT tokens containing tenant context
- **Authorization**: Role-based permissions (Admin, Technician, Pathologist)

**Service Boundary:** All identity, access, and multi-tenancy concerns are owned by this service.

---

## Features

### Feature 1: Tenant Management

**What It Does:**
Allows creation and management of isolated laboratory organizations (tenants). Each tenant operates independently with complete data segregation.

**User Stories:**

1. **As a system administrator**, I want to create a new laboratory tenant with an initial admin user so that the laboratory can start using the system immediately.

2. **As a laboratory administrator**, I want to configure my laboratory's settings so that the system works according to our procedures.

3. **As a laboratory administrator**, I want assurance that my laboratory's data is completely isolated from other laboratories so that patient confidentiality is maintained.

**Requirements:**
- Support creation of new tenant organizations
- Each tenant must have unique identifier and name
- When creating a tenant, a first admin user must be created simultaneously
- Tenant configuration includes: name, description, status (active/inactive)
- Each tenant can configure their own LIS connection parameters
- Each tenant can define their own verification rules

**Acceptance Criteria:**
- [ ] System administrator can create a new tenant with name and description
- [ ] During tenant creation, first admin user is created with name, email, and password
- [ ] New tenant is initialized with default verification rules
- [ ] First admin user can log in immediately after tenant creation
- [ ] Tenant can be activated or deactivated
- [ ] Deleting a tenant removes all associated data (users, samples, results, reviews)
- [ ] Users from Tenant A cannot see any data from Tenant B

**Business Rules:**
- Tenant names must be unique across the system
- A tenant must have at least one admin user
- Inactive tenants cannot access the system
- LIS connection credentials must be stored securely

---

### Feature 2: User & Access Management

**What It Does:**
Manages user accounts and controls what users can see and do based on their role.

**User Stories:**

1. **As a laboratory administrator**, I want to create user accounts for my staff so they can access the system.

2. **As a user**, I want to log in securely so that only authorized people can access laboratory data.

3. **As a laboratory administrator**, I want to assign roles to users so that they have appropriate permissions for their job function.

**Requirements:**
- Support three user roles: Admin, Technician, Pathologist
- Users authenticate with email and password
- Users can only access data for their own laboratory (tenant)
- Passwords must be stored securely
- User sessions must expire after inactivity

**Role Capabilities:**

| Role | Can Do |
|------|--------|
| **Admin** | Manage users, configure verification rules, configure LIS, view all data |
| **Technician** | View samples/results, perform reviews, see review queue |
| **Pathologist** | View samples/results, handle escalations, provide clinical oversight |

**Acceptance Criteria:**
- [ ] Users can log in with email and password
- [ ] Invalid login attempts are rejected with clear error message
- [ ] Admin users can create, update, and deactivate other users
- [ ] Users can only see data for their own laboratory
- [ ] User sessions expire after 8 hours of inactivity
- [ ] Admin can change a user's role
- [ ] Deactivated users cannot log in

**Business Rules:**
- Email addresses must be unique within a laboratory
- Users must belong to exactly one laboratory
- Passwords must meet minimum complexity requirements
- Users cannot change their own role
- At least one admin user must exist per tenant

---

## Data Entities Owned

### Tenant
Represents a laboratory or organization. Each tenant operates independently with complete data isolation.

**Key Attributes:**
- Unique identifier (UUID)
- Name (unique across system)
- Description
- Status (active/inactive)
- LIS configuration (JSON, encrypted)
- Timestamps (created_at, updated_at)

**Key Relationships:**
- One tenant has many users
- One tenant has many samples (via LIS Integration Service)
- One tenant has many verification rules (via Verification Service)

---

### User
A person with access to the system. Belongs to exactly one tenant. Has a role that determines permissions.

**Key Attributes:**
- Unique identifier (UUID)
- Tenant ID (foreign key, NOT NULL)
- Email (unique within tenant)
- Password hash (bcrypt)
- Name
- Role (Admin | Technician | Pathologist)
- Active status
- Last login timestamp
- Timestamps (created_at, updated_at)

**Key Relationships:**
- Each user belongs to exactly one tenant
- One user can perform many reviews (via Verification Service)

---

## API Endpoints

Based on [PROPOSED-ARCHITECTURE.md](PROPOSED-ARCHITECTURE.md), the Platform Service exposes:

### Tenant Management
- `POST /api/v1/tenants` - Create tenant with first admin user
- `GET /api/v1/tenants/{id}` - Get tenant details (admin only)
- `PUT /api/v1/tenants/{id}` - Update tenant (admin only)
- `DELETE /api/v1/tenants/{id}` - Delete tenant (admin only)

### Authentication
- `POST /api/v1/auth/login` - Login (returns JWT with tenant_id and role)
- `POST /api/v1/auth/refresh` - Refresh JWT token
- `GET /api/v1/auth/me` - Get current user info

### User Management
- `GET /api/v1/users` - List users for tenant (admin only)
- `POST /api/v1/users` - Create user (admin only)
- `GET /api/v1/users/{id}` - Get user details
- `PUT /api/v1/users/{id}` - Update user (admin only)
- `DELETE /api/v1/users/{id}` - Deactivate user (admin only)
- `POST /api/v1/users/{id}/password` - Change password

---

## Multi-Tenancy Implementation

The Platform Service is responsible for:

1. **Tenant Context in JWT Tokens:**
   - Every JWT token includes `tenant_id` in the payload
   - All API requests extract `tenant_id` from the validated token
   - No cross-tenant data access is possible

2. **Repository-Level Isolation:**
   - All repositories enforce tenant filtering on queries
   - Composite unique constraints: (email, tenant_id) for users
   - Foreign key: user.tenant_id → tenant.id

3. **API Gateway Integration:**
   - Platform Service validates JWT tokens for all services
   - Token validation endpoint: `POST /api/v1/auth/validate`
   - Returns user identity, tenant_id, and role for authorization

---

## Cross-Cutting Concerns (Service-Specific)

### Multi-Tenancy
- Enforces tenant isolation at repository level
- All user queries automatically scoped to tenant_id from JWT
- Composite unique constraints on email per tenant

### Authentication
- Issues JWT tokens with embedded tenant_id and role
- Token expiration: 8 hours
- Bcrypt password hashing with salt rounds = 12

### Authorization
- Role-based access control (RBAC)
- Three roles: Admin, Technician, Pathologist
- Role enforcement at API endpoint level via decorators

### Security
- Passwords hashed with bcrypt (industry standard)
- LIS credentials encrypted at rest (AES-256)
- JWT tokens signed with HS256 algorithm
- Failed login attempts logged for security monitoring

---

## Non-Functional Requirements (Service-Specific)

### Performance
- Authentication completes within 200ms
- User lookup by email within 50ms
- Support 50+ concurrent users per tenant
- JWT token generation < 100ms

### Scalability
- Horizontal scaling via stateless design
- Database connection pooling (min: 5, max: 20)
- Support at least 10 tenants per deployment

### Reliability
- No single point of failure
- Database transactions for atomic tenant + user creation
- Graceful degradation if authentication service unavailable

### Security
- Password complexity: minimum 8 characters, uppercase, lowercase, digit, special character
- Session timeout: 8 hours of inactivity
- JWT secret key rotation supported
- Audit log for all user management operations

---

## Implementation References

- **Architecture Principles:** [ARCHITECTURE-CORE.md](ARCHITECTURE-CORE.md) - Hexagonal architecture with ports & adapters
- **Multi-Tenancy Patterns:** [ARCHITECTURE-MULTITENANCY.md](ARCHITECTURE-MULTITENANCY.md) - Tenant isolation strategies
- **Code Examples:** [ARCHITECTURE-EXAMPLES.md](ARCHITECTURE-EXAMPLES.md) - Sample implementations
- **Service Decomposition:** [PROPOSED-ARCHITECTURE.md](PROPOSED-ARCHITECTURE.md), lines 15-44

---

## Testing Strategy

### Unit Tests
- Test all business logic in services (TenantService, UserService, AuthService)
- Mock all repository dependencies
- Test password validation rules
- Test email normalization
- Test role-based authorization logic

### Integration Tests
- Test PostgreSQL repositories with real database
- Test multi-tenant isolation at database level
- Test composite unique constraints
- Test JWT token generation and validation
- Test tenant + user atomic creation

### API Tests
- Test all endpoints with TestClient
- Test authentication requirements
- Test tenant_id scoping
- Test role-based access control
- Test error handling and validation

---

## Dependencies on Other Services

The Platform Service is foundational and **does not depend on other services**. However:

- **LIS Integration Service** depends on Platform Service for:
  - User authentication (JWT validation)
  - Tenant existence validation

- **Verification Service** depends on Platform Service for:
  - User authentication (JWT validation)
  - Tenant existence validation
  - User identity for review attribution

---

*This specification details the Platform Service implementation requirements. Refer to [SPECIFICATION.md](SPECIFICATION.md) for system-wide vision, cross-cutting concerns, and success metrics.*
