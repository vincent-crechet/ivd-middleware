# Instrument Integration Service - Specification

*Part of IVD Middleware. See [SPECIFICATION.md](SPECIFICATION.md) for system overview, cross-cutting concerns, and global non-functional requirements.*

---

## Service Responsibility

The Instrument Integration Service enables IVD Middleware to communicate with analytical laboratory instruments via HTTP REST APIs. It manages the bidirectional flow of test orders and analytical results between instruments and the middleware. It handles:

- **Instrument Connection Management**: Configure and manage connections to analytical instruments
- **Host Query Reception**: Receive test order queries from instruments and return pending work
- **Result Reception**: Receive test results from instruments
- **Order Management**: Manage test orders from LIS that instruments will execute
- **Result Storage**: Store instrument results and trigger verification workflows
- **Duplicate Detection**: Prevent duplicate result ingestion from instruments

**Service Boundary:** All instrument communication logic, order/result storage from instruments, and instrument-specific data operations are owned by this service.

**Note:** This service is the NEW MVP addition to support instrument integration that was previously marked "out of scope".

---

## Features

### Feature 9: Instrument Query Reception (Host Queries)

**What It Does:**
Receives test order queries from analytical instruments via HTTP REST APIs and returns pending work for execution.

**User Stories:**

1. **As an instrument operator**, I want my instrument to automatically request pending test orders from the middleware so that work flows from the LIS to the instrument without manual intervention.

2. **As a laboratory administrator**, I want to register new instruments in the system so that they can communicate with the middleware.

3. **As a laboratory administrator**, I want to monitor instrument connection status so that I can quickly identify and resolve connectivity issues.

**Requirements:**
- Receive host query requests from instruments via HTTP REST API
- Return pending test orders for requested patient/sample to instrument
- Query authentication using per-instrument API tokens
- Instrument connection health monitoring and status tracking
- Support multiple concurrent instrument connections per tenant
- Track query history for audit purposes

**Acceptance Criteria:**
- [ ] Lab admin can register new instrument with name, type, and API token
- [ ] Instrument can query pending orders via `POST /api/v1/instruments/query-host`
- [ ] Query request includes: patient_id or sample_barcode
- [ ] System returns list of pending test orders for that patient/sample
- [ ] Each returned order includes: order_id, test_code, sample_info, patient_demographics
- [ ] Unauthenticated requests are rejected with 401 Unauthorized
- [ ] Invalid token format returns 400 Bad Request
- [ ] Query response includes: list of orders, query_timestamp, instrument_status
- [ ] Query history is logged for audit trail
- [ ] Lab admin can view instrument connection status
- [ ] System tracks last successful query timestamp per instrument

**Business Rules:**
- Each instrument has unique API token (UUID, encrypted at rest)
- Instruments must be registered before queries are accepted
- Only pending orders are returned (status = "pending")
- Orders are returned in FIFO order (oldest first)
- Query responses are immediate (no batching delays)
- Failed queries do not affect other instruments' operations
- Instrument must be active to receive orders
- Tokens are rotatable by admin

---

### Feature 10: Instrument Result Reception

**What It Does:**
Receives test results from analytical instruments via HTTP REST APIs, validates them, stores them, and triggers the verification workflow.

**User Stories:**

1. **As an instrument operator**, I want my instrument to send test results directly to the middleware so that results flow automatically to the verification workflow.

2. **As a laboratory administrator**, I want duplicate results to be detected and prevented so that result data stays clean and consistent.

3. **As a lab technician**, I want results from instruments to appear in the verification queue automatically so that I can review them quickly.

**Requirements:**
- Receive result data from instruments via HTTP REST API
- Validate result format and content
- Store results with complete metadata
- Detect and prevent duplicate results
- Automatically trigger verification workflow on new results
- Track result ingestion status and audit trail

**Acceptance Criteria:**
- [ ] Instrument can send results via `POST /api/v1/instruments/results`
- [ ] Request authentication uses per-instrument API token
- [ ] Result payload includes: test_code, value, unit, reference_range, flags, timestamp
- [ ] System validates result format before storage
- [ ] Duplicate results are detected based on (external_result_id, tenant_id, instrument_id)
- [ ] Duplicate results are silently skipped (idempotent)
- [ ] Valid results return 202 Accepted with result_id
- [ ] Invalid/malformed results return 400 Bad Request with error details
- [ ] Unauthenticated requests return 401 Unauthorized
- [ ] Results are linked to correct sample automatically
- [ ] Verification workflow is triggered immediately upon receipt
- [ ] Result ingestion is logged for audit trail

**Business Rules:**
- Results must include valid test_code
- Results must include numeric or text value
- Collection timestamp must be <= received timestamp
- Results are immutable after creation
- Duplicate detection is per-tenant and per-instrument
- Only active instruments can submit results
- Results that don't match any pending order are stored with warning status
- Auto-verification is triggered within 1 second of result receipt

---

## Data Entities Owned

### Instrument

Configuration for an analytical instrument connected to the middleware.

**Key Attributes:**
- Unique identifier (UUID)
- Tenant ID (foreign key, NOT NULL)
- Instrument name (text)
- Instrument type (e.g., "Hematology", "Chemistry", "Immunoassay")
- API token (UUID, encrypted at rest, unique per instrument)
- API token created_at (timestamp)
- Connection status (active, inactive, disconnected)
- Last successful query timestamp (nullable)
- Last successful result timestamp (nullable)
- Failure count (integer, default 0)
- Last failure timestamp (nullable)
- Last failure reason (text, nullable)
- Timestamps (created_at, updated_at)

**Key Relationships:**
- Each instrument belongs to exactly one tenant
- One instrument can have many orders (from LIS)
- One instrument can have many results (queries and responses)

**Business Rules:**
- Instrument names are unique within a tenant
- API tokens are unique across the system
- Only one active API token per instrument at a time
- Instruments can be deactivated but not deleted (audit trail)

---

### Order

A test order from the external LIS that an instrument will execute.

**Key Attributes:**
- Unique identifier (UUID)
- Tenant ID (foreign key, NOT NULL)
- External LIS order ID (from source LIS system)
- Sample ID (foreign key to samples table, NOT NULL)
- Patient ID (text)
- Test codes (list of test codes to perform)
- Priority (routine, stat, critical)
- Status (pending, in_progress, completed, failed, cancelled)
- Assigned instrument ID (nullable, which instrument is executing this order)
- Created by (LIS or manual entry)
- Timestamps (created_at, assigned_at, completed_at, updated_at)

**Key Relationships:**
- Each order belongs to exactly one tenant
- Each order references exactly one sample
- Each order may be assigned to one instrument
- Order may have many result entries (one per test)

**Business Rules:**
- Orders are created when LIS sends sample/test data
- Orders transition: pending → in_progress (when instrument queries) → completed (when results received)
- Only pending orders are returned to instruments
- Orders are immutable once completed
- Orders can be cancelled manually by admin

---

### InstrumentQuery

Audit log of host queries received from instruments.

**Key Attributes:**
- Unique identifier (UUID)
- Tenant ID (foreign key, NOT NULL)
- Instrument ID (foreign key, NOT NULL)
- Query timestamp (when received)
- Patient/Sample query parameter (what was requested)
- Orders returned count (how many orders were returned)
- Response timestamp (when response was sent)
- Response status (success, error, timeout)
- Error reason (nullable)

**Key Relationships:**
- Each query belongs to exactly one tenant
- Each query is from exactly one instrument

**Business Rules:**
- Queries are logged in real-time
- One audit entry per query
- Queries are immutable (audit trail)

---

## Instrument Adapters

The service implements the **Adapter Pattern** for instrument communication:

### IInstrumentAdapter Interface
```
# Connection management
- authenticate_instrument(api_token: str) -> Instrument
- test_connection() -> ConnectionStatus

# Receive queries (inbound)
- get_pending_orders(patient_id: str, instrument_id: str) -> List[Order]
- mark_order_in_progress(order_id: str) -> bool

# Receive results (inbound)
- process_results(result_data: Dict) -> ProcessingStatus
- validate_result_format(result_data: Dict) -> bool
```

### Adapter Implementations

#### 1. RESTAPIInstrumentAdapter
- Primary adapter for HTTP/REST instrument communication
- Validates incoming requests
- Returns order and result responses
- Supports JSON request/response format

#### 2. MockInstrumentAdapter
- Generates realistic test queries and results
- No real instrument connection required
- Useful for development and testing
- Supports configurable scenarios

---

## API Endpoints

Based on [PROPOSED-ARCHITECTURE.md](PROPOSED-ARCHITECTURE.md), the Instrument Integration Service exposes:

### Instrument Management
- `POST /api/v1/instruments/register` - Register new instrument (admin only)
  - Request: name, type, api_token (optional - system generates if not provided)
  - Returns: instrument_id, api_token
- `GET /api/v1/instruments` - List all instruments for tenant (admin only)
- `GET /api/v1/instruments/{id}` - Get instrument details
- `GET /api/v1/instruments/{id}/status` - Get current instrument connection status
- `PUT /api/v1/instruments/{id}` - Update instrument configuration (admin only)
- `DELETE /api/v1/instruments/{id}` - Deactivate instrument (admin only, soft delete)

### Host Queries (Instrument Queries for Orders)
- `POST /api/v1/instruments/query-host` - **Instrument queries for pending orders**
  - Authentication: `X-Instrument-Token: {api_token}` header
  - Request body: `{ "patient_id": "...", "sample_barcode": "..." }`
  - Returns 200 OK with list of pending orders OR empty list if none pending
  - Response: `{ "orders": [...], "query_timestamp": "...", "instrument_status": "active" }`

### Result Reception
- `POST /api/v1/instruments/results` - **Instrument sends test results**
  - Authentication: `X-Instrument-Token: {api_token}` header
  - Request body: result data with test_code, value, unit, reference_range, flags
  - Returns 202 Accepted with result_id if valid
  - Returns 400 Bad Request with error details if invalid
  - Response: `{ "result_id": "...", "status": "accepted", "verification_queued": true }`

### Query History & Audit
- `GET /api/v1/instruments/{id}/query-history` - Get instrument query audit log (admin only)
  - Query params: `start_date`, `end_date`, `limit`, `offset`
  - Returns: list of queries with timestamps and results
- `GET /api/v1/instruments/{id}/result-history` - Get results submitted by instrument (admin only)
  - Query params: `start_date`, `end_date`, `limit`, `offset`
  - Returns: list of results with submission status

---

## Multi-Tenancy Implementation

1. **Tenant Scoping:**
   - All instruments have `tenant_id` foreign key
   - All queries automatically filter by `tenant_id` from JWT
   - Instrument configurations are unique per tenant

2. **API Token per Instrument:**
   - Each instrument has unique API token (UUID)
   - Tokens are encrypted at rest (AES-256)
   - Tokens are rotatable by admin
   - Token used for both query and result authentication

3. **Data Isolation:**
   - Composite unique index: (api_token, tenant_id)
   - All instrument queries filter by tenant_id
   - Instruments cannot see orders or results from other tenants
   - No cross-tenant communication possible

---

## Cross-Cutting Concerns (Service-Specific)

### Multi-Tenancy
- All instrument/order/result queries scoped to tenant_id from JWT
- Instrument configuration isolated per tenant
- API token validation includes tenant_id check

### Authentication
- Validates instrument API tokens for all HTTP endpoints
- Instruments authenticated via token in `X-Instrument-Token` header
- Token format: UUID (case-insensitive)
- Invalid/expired tokens return 401 Unauthorized

### Data Integrity
- Duplicate detection on (external_result_id, tenant_id, instrument_id)
- Orders must reference valid samples
- Results must reference valid orders (if order_id provided)
- Foreign key constraints enforced
- Validation: sample_collection_date <= result_timestamp

### Error Handling
- Log all instrument connection errors with details
- Graceful handling of malformed requests
- Retry logic for transient failures
- Clear error responses for debugging

---

## Non-Functional Requirements (Service-Specific)

### Performance
- Host query response < 500ms (return pending orders)
- Result ingestion < 1 second (process and store)
- Duplicate detection < 100ms per result
- Support 50+ instruments per tenant
- Support 100+ queries per minute per instrument

### Scalability
- Horizontal scaling via stateless design
- Connection pooling for database
- Database indexing on: (tenant_id, instrument_id), (external_result_id, tenant_id)
- Support at least 1000 orders per instrument
- Support at least 10,000 results per instrument per day

### Reliability
- Failed result submissions do not block next submission
- Duplicate results handled gracefully (silently skipped)
- Instrument connectivity failures do not affect other instruments
- Query/result endpoints always respond (even if database is slow)

### Security
- API tokens encrypted at rest (AES-256)
- Never log or expose API tokens in UI/responses
- Validate and sanitize all incoming instrument data
- Rate limiting per instrument (configurable)
- Tokens expire after N days (configurable, default: 90 days)

---

## Integration with Other Services

### Depends On:
- **Platform Service**:
  - User authentication (JWT validation)
  - Tenant existence validation
- **LIS Integration Service**:
  - Orders (test orders from LIS that instruments will execute)
  - Sample data (patient info, specimen details)

### Provides To:
- **LIS Integration Service**:
  - Results from instruments (for uploading back to external LIS)
  - Order status updates (pending → in_progress → completed)
- **Verification Service**:
  - New results for auto-verification
  - Patient history from instruments

**Communication Patterns:**
- **With LIS Service:**
  - Shares `Order` model from `shared/models/order.py` (canonical source of truth)
    - LIS Integration: Creates orders from external LIS systems (owner)
    - Instrument Integration: Assigns orders to instruments and tracks execution
  - Order fields: `patient_id`, `test_codes` (JSON array), `priority`, `assigned_instrument_id`, `status`
  - Reads/updates `orders` table (LIS writes, Instrument reads and updates assignment/status)
  - Writes `instrument_results` table (Instrument writes, Verification reads)
  - When Instrument Service receives results, LIS Service is triggered to send them to external LIS
- **With Verification Service:**
  - Results written by Instrument Service trigger Verification Service auto-verification
  - Event-driven (Phase 2): Instrument publishes "NewResultFromInstrument" event → Verification consumes

---

## Testing Strategy

### Unit Tests
- Test each instrument adapter independently
- Mock instrument HTTP requests
- Test duplicate detection logic
- Test data validation
- Test error responses

### Integration Tests
- Test with mock instrument adapter
- Test query/result flow with real database
- Test multi-tenant isolation (tenant A cannot see tenant B's instruments)
- Test order delivery accuracy
- Test result ingestion accuracy

### End-to-End Tests
- Test complete flow: LIS order → Instrument query → Instrument result → Verification
- Test error scenarios: bad tokens, malformed results, network timeouts
- Test concurrent instruments querying simultaneously
- Test result deduplication across multiple submissions

---

*This specification defines how the Instrument Integration Service enables communication between analytical instruments and the IVD Middleware, completing the MVP's end-to-end data flow from LIS through instruments and back.*
