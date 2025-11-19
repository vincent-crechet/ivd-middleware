# LIS Integration Service - Specification

*Part of IVD Middleware. See [SPECIFICATION.md](SPECIFICATION.md) for system overview, cross-cutting concerns, and global non-functional requirements.*

---

## Service Responsibility

The LIS Integration Service connects external Laboratory Information Systems (LIS) to the IVD Middleware and manages bidirectional communication of sample, result, and order data. It handles:

- **LIS Connection Management**: Configure and maintain connections to external LIS systems
- **Data Ingestion (Receive)**: Retrieve samples and results from LIS (push and pull models)
- **Data Export (Send)**: Upload verified and reviewed results back to LIS
- **Data Normalization**: Transform LIS data into standardized format
- **Duplicate Detection**: Prevent re-importing existing samples/results
- **Sample & Result Querying**: Provide search and filtering capabilities
- **Order Management**: Manage test orders from LIS that instruments will execute

**Service Boundary:** All LIS adapter logic (bidirectional), sample/result/order storage, and query operations are owned by this service.

---

## Features

### Feature 3: Sample & Result Ingestion

**What It Does:**
Retrieves laboratory samples and test results from external LIS systems and stores them in the middleware.

**User Stories:**

1. **As a laboratory administrator**, I want new results to appear automatically in the system so that staff don't need to manually import data.

2. **As a lab technician**, I want to see all samples and their results so that I can track what needs review.

3. **As a lab technician**, I want to search for specific samples by patient or date so that I can quickly find what I need.

**Requirements:**
- System must retrieve samples and results from configured LIS
- Support multiple LIS connection types (mock, file upload, REST API)
- Prevent duplicate results from being created
- Associate results with their corresponding sample
- Support searching and filtering of samples

**Acceptance Criteria:**
- [ ] System retrieves new samples from LIS automatically
- [ ] Each sample includes: patient identifier, specimen type, collection date
- [ ] Each result includes: test name, value, unit, reference range, flags
- [ ] Duplicate results are detected and not re-imported
- [ ] Users can search samples by patient ID
- [ ] Users can filter samples by date range
- [ ] Users can filter samples by status (pending, verified, needs review)
- [ ] Sample details show all associated results

**Business Rules:**
- A sample can have multiple results (one per test)
- Results must be linked to a valid sample
- Duplicate detection based on: external LIS ID, test code, and sample
- Collection date must be before or equal to received date
- Results are immutable once verified

---

### Feature 4: LIS Integration

**What It Does:**
Connects to external Laboratory Information Systems to retrieve sample and result data. Supports both push (LIS sends data to middleware) and pull (middleware retrieves data from LIS) models.

**User Stories:**

1. **As a laboratory administrator**, I want to configure how my laboratory's LIS connects to the middleware so that data flows automatically.

2. **As a laboratory administrator**, I want the LIS to send orders directly to the middleware so that we have real-time data without polling delays.

3. **As a laboratory administrator**, I want to be notified if the LIS connection fails so that I can fix the problem quickly.

4. **As a laboratory administrator**, I want to test the LIS connection so that I can verify configuration is correct.

**Requirements:**
- Support configuration of LIS connection per tenant
- Support two integration models:
  - **Push Model**: LIS sends samples and results to middleware API endpoints
  - **Pull Model**: Middleware retrieves data from LIS periodically
- Handle temporary LIS connection failures gracefully (pull model)
- Validate and authenticate incoming data (push model)
- Log all LIS communication errors
- Support these initial LIS types:
  - Mock adapter (generates test data)
  - File upload (CSV import)
  - REST API incoming (push model - LIS calls middleware)
  - REST API outgoing (pull model - middleware calls LIS)
- Retrieve only new data since last successful retrieval (pull model)

**Acceptance Criteria:**
- [ ] Lab admin can configure LIS connection parameters
- [ ] Lab admin can select integration model (push or pull)
- [ ] Lab admin can select LIS type from supported options
- [ ] **Push Model**: Middleware exposes API endpoint to receive incoming orders
- [ ] **Push Model**: Incoming orders are authenticated using tenant API key
- [ ] **Push Model**: Invalid or unauthenticated requests are rejected
- [ ] **Push Model**: Successfully received orders are processed immediately
- [ ] **Pull Model**: System attempts to retrieve data at configured intervals
- [ ] **Pull Model**: Failed connections are retried automatically
- [ ] Failed connections or invalid data are logged with error details
- [ ] Lab admin receives notification after 3 consecutive failures (pull model)
- [ ] Connection credentials and API keys are never exposed in logs or UI

**Business Rules:**
- Each tenant can have only one active LIS connection
- Tenants using push model must have a unique API key for authentication
- API keys must be generated by the system (not user-provided)
- Pull model: retrieval interval is configurable per tenant (minimum: 1 minute, default: 5 minutes)
- Push model: orders can be received at any time
- Failed retrievals must not lose data or create duplicates
- Connection credentials and API keys must be encrypted at rest
- Duplicate detection applies to both push and pull models

---

### Feature 8: Send Results to LIS (Bidirectional Communication)

**What It Does:**
Uploads verified and reviewed results back to the external LIS system, enabling bidirectional data flow between middleware and LIS.

**User Stories:**

1. **As a laboratory administrator**, I want verified results to be automatically sent back to the LIS so that the LIS stays synchronized with verification decisions.

2. **As a laboratory administrator**, I want to configure whether results are automatically uploaded or require manual approval so that we maintain control over what goes back to the LIS.

3. **As a laboratory administrator**, I want to see which results have been successfully sent to the LIS and which failed so that I can monitor data flow.

**Requirements:**
- Support uploading verified results back to external LIS
- Support two upload modes:
  - **Automatic**: Results automatically uploaded when verification is complete
  - **Manual**: Results uploaded only when explicitly approved by admin
- Track upload status for each result (pending, sent, failed, acknowledged)
- Retry mechanism for failed uploads with exponential backoff
- Validate that all results match verification status in LIS
- Log all upload attempts and failures

**Acceptance Criteria:**
- [ ] Lab admin can configure auto-upload vs manual upload per tenant
- [ ] Lab admin can choose which verification statuses to upload (verified, rejected, both)
- [ ] System automatically uploads results when auto-upload is enabled
- [ ] Lab admin can manually trigger upload of pending results
- [ ] Each result tracks: upload status, last upload attempt timestamp, failure reason
- [ ] Failed uploads retry automatically (exponential backoff: 1 min, 2 min, 4 min, 8 min)
- [ ] Lab admin is notified after 3 consecutive failures for a result
- [ ] LIS connection health is verified before attempting upload
- [ ] Bulk upload operations are supported (upload multiple results at once)

**Business Rules:**
- Only verified or rejected results can be uploaded (status = "verified" or "rejected")
- Results can only be uploaded once successfully (idempotent)
- Failed uploads do not block other operations
- Auto-upload requires at least one successful ping to LIS in the last hour
- Uploads respect rate limits defined in LIS configuration
- Once uploaded, original result data in middleware cannot be modified

---

### Feature 7 (Partial): Sample & Result Querying

**What It Does:**
Allows users to search, filter, and view samples and their associated results.

**User Stories:**

1. **As a lab technician**, I want to search for a specific patient's samples so that I can check their results.

2. **As a lab technician**, I want to filter samples by date so that I can see recent work.

3. **As a pathologist**, I want to view a sample with all its results and review history so that I can understand the full context.

**Requirements:**
- Search samples by patient identifier
- Filter samples by date range
- Filter samples by status (pending, verified, needs review, rejected)
- Filter samples by specimen type
- View sample details with all associated results
- View result details with verification and review information

**Acceptance Criteria:**
- [ ] Users can search by patient ID (partial match)
- [ ] Users can filter by collection date range
- [ ] Users can filter by current status
- [ ] Search results show: sample ID, patient ID, collection date, status, number of results
- [ ] Clicking a sample shows all its results
- [ ] Each result shows: test name, value, unit, reference range, flags, verification status
- [ ] For verified results, show whether auto-verified or manually reviewed
- [ ] For manually reviewed results, show reviewer name, decision, and comments
- [ ] Users can only query data for their own laboratory

**Business Rules:**
- Search is case-insensitive
- Date filters are inclusive (include start and end dates)
- Results are sorted by collection date (newest first)
- Users cannot view samples from other laboratories

**Note:** Verification status and review information are provided by the Verification Service. This service focuses on sample/result data retrieval and basic filtering.

---

## Data Entities Owned

### Sample
A physical specimen submitted to the laboratory for testing. Contains patient identification and specimen details.

**Key Attributes:**
- Unique identifier (UUID)
- Tenant ID (foreign key, NOT NULL)
- External LIS ID (from source system)
- Patient identifier (anonymized or direct)
- Specimen type (blood, urine, etc.)
- Collection date/time
- Received date/time
- Status (pending, verified, needs_review, rejected)
- Timestamps (created_at, updated_at)

**Key Relationships:**
- Each sample belongs to exactly one tenant
- One sample has many results

---

### Result
The analytical outcome of a test performed on a sample. Includes measured value, reference range, and verification status.

**Key Attributes (Verification):**
- Unique identifier (UUID)
- Sample ID (foreign key, NOT NULL)
- Tenant ID (foreign key, NOT NULL, denormalized for query performance)
- External LIS result ID
- Test code (e.g., "GLU" for glucose)
- Test name
- Value (numeric or text)
- Unit (mg/dL, mmol/L, etc.)
- Reference range (low, high)
- LIS flags (H, L, C, etc.)
- Verification status (pending, verified, needs_review, rejected)
- Verification method (auto, manual, null)
- Timestamps (created_at, verified_at)

**Key Attributes (Upload to LIS - NEW):**
- Upload status (pending, sent, failed, acknowledged)
- Sent to LIS at (timestamp, nullable)
- Last upload attempt at (timestamp, nullable)
- Upload failure count (integer, default 0)
- Upload failure reason (text, nullable)

**Key Relationships:**
- Each result belongs to exactly one sample
- Each result belongs to exactly one tenant
- One result may have zero or one review (via Verification Service)

**Immutability:**
- Results are immutable once verified (verification_status = "verified" or "rejected")
- Updates to verified results are not permitted

---

### LIS Configuration (Per Tenant)
Configuration for connecting to a laboratory's LIS system, including bidirectional communication settings.

**Key Attributes (Receive Side):**
- Tenant ID (foreign key, unique)
- LIS type (mock, file_upload, rest_api_push, rest_api_pull)
- Integration model (push, pull)
- API endpoint URL (for pull model)
- API authentication (credentials, encrypted)
- Tenant API key (for push model, encrypted)
- Pull interval (minutes)
- Last successful retrieval timestamp
- Connection status (active, inactive, failed)
- Failure count

**Key Attributes (Send Side):**
- Auto-upload enabled (boolean, default: false)
- Upload verified results (boolean)
- Upload rejected results (boolean)
- Upload batch size (number of results per batch)
- Upload rate limit (max results per minute)
- Last successful upload timestamp
- Last upload failure timestamp
- Upload failure count
- Timestamps (created_at, updated_at)

---

## LIS Adapters

The service implements the **Adapter Pattern** for LIS connections:

### ILISAdapter Interface
```
# Receive side (inbound)
- connect(): bool
- get_samples(since: datetime): List[Sample]
- get_results(sample_id): List[Result]
- test_connection(): ConnectionStatus

# Send side (outbound - new for bidirectional)
- send_results(results: List[Result]) -> SendStatus
- acknowledge_results(result_ids: List[str]) -> bool
```

### Adapter Implementations

#### 1. MockLISAdapter
- Generates realistic test data
- No external connection required
- Useful for development and demos

#### 2. FileUploadAdapter
- Accepts CSV file uploads
- Parses and validates format
- Imports samples and results

#### 3. RESTAPIIncomingAdapter (Push Model)
- Receives POST requests from external LIS
- Validates tenant API key
- Processes incoming orders immediately
- Returns acknowledgment

#### 4. RESTAPIOutgoingAdapter (Pull Model)
- Calls external LIS REST API periodically
- Authenticates with LIS credentials
- Retrieves new data since last successful pull
- Handles pagination if supported

---

## API Endpoints

Based on [PROPOSED-ARCHITECTURE.md](PROPOSED-ARCHITECTURE.md), the LIS Integration Service exposes:

### LIS Configuration
- `POST /api/v1/lis/config` - Configure LIS connection for tenant (admin only)
- `GET /api/v1/lis/config` - Get current LIS configuration (admin only)
- `PUT /api/v1/lis/config` - Update LIS configuration (admin only)
- `GET /api/v1/lis/connection-status` - Test LIS connection health

### Data Ingestion (Push Model)
- `POST /api/v1/lis/ingest` - **Push endpoint** - Receives orders from external LIS
  - Authenticates using tenant API key in header: `X-API-Key: {key}`
  - Validates incoming data format
  - Returns 202 Accepted if valid, 400/401 if invalid

### Manual Upload
- `POST /api/v1/lis/manual-upload` - Upload CSV file with samples/results (admin only)

### Sample & Result Querying
- `GET /api/v1/samples` - List samples for tenant with filtering
  - Query params: `patient_id`, `start_date`, `end_date`, `status`, `limit`, `offset`
- `GET /api/v1/samples/{id}` - Get sample details
- `GET /api/v1/samples/{id}/results` - Get all results for a sample
- `GET /api/v1/results/{id}` - Get result details

### Data Export (Send Results to LIS)
- `POST /api/v1/lis/send-results` - Upload verified/reviewed results to LIS (admin only)
  - Request body: list of result IDs to send, optional filters
  - Returns: batch_id, count_sent, count_failed, retry_schedule
- `GET /api/v1/lis/send-status` - Get upload status and sync state (admin only)
  - Query params: `start_date`, `end_date`, `status` (pending, sent, failed, acknowledged)
  - Returns: list of results with upload status
- `POST /api/v1/lis/retry-failed` - Retry uploading failed results (admin only)
  - Request body: optional filters (result_ids, start_date, end_date)
  - Returns: retry_job_id, count_scheduled_for_retry
- `PUT /api/v1/lis/config/upload-settings` - Update auto-upload configuration (admin only)
  - Request body: auto_upload_enabled, upload_verified, upload_rejected, batch_size, rate_limit
  - Returns: updated LIS configuration

---

## Multi-Tenancy Implementation

1. **Tenant Scoping:**
   - All samples and results have `tenant_id` foreign key
   - All queries automatically filter by `tenant_id` from JWT
   - LIS configuration is unique per tenant

2. **API Key per Tenant (Push Model):**
   - Each tenant has a unique API key for push model
   - API keys are UUIDs generated by the system
   - Keys are encrypted at rest (AES-256)
   - Keys are rotatable by admin

3. **Data Isolation:**
   - Composite unique index: (external_lis_id, tenant_id) for samples
   - Composite unique index: (external_lis_result_id, tenant_id) for results
   - No cross-tenant queries possible

---

## Cross-Cutting Concerns (Service-Specific)

### Multi-Tenancy
- All sample/result queries scoped to tenant_id from JWT
- LIS configuration isolated per tenant
- Duplicate detection scoped within tenant

### Authentication
- Validates JWT tokens via Platform Service
- Push model uses tenant-specific API keys
- Pull model uses encrypted LIS credentials

### Data Integrity
- Duplicate detection on (external_lis_id, tenant_id)
- Results must reference valid samples
- Foreign key constraints enforced
- Validation: collection_date <= received_date

### Error Handling
- Log all LIS connection failures with details
- Retry logic for pull model (exponential backoff)
- Notify admin after 3 consecutive failures
- Graceful degradation if LIS temporarily unavailable

---

## Non-Functional Requirements (Service-Specific)

### Performance
- LIS retrieval completes within 5 minutes for up to 1000 new results
- Duplicate detection < 100ms per result
- Sample search with filters < 2 seconds
- Support 1000+ samples per tenant

### Scalability
- Horizontal scaling via stateless design
- Background task queue for pull model (Celery + RabbitMQ)
- Database indexing on: (tenant_id, patient_id), (tenant_id, collection_date)
- Support at least 10,000 samples per tenant

### Reliability
- Failed LIS retrievals retry automatically (pull model)
- No data loss on system restart
- Idempotent ingestion (duplicate detection)
- Transaction rollback if sample + results fail together

### Security
- LIS credentials encrypted at rest (AES-256)
- API keys for push model encrypted at rest
- Never log or expose credentials in UI
- Validate and sanitize all incoming LIS data

---

## Integration with Other Services

### Depends On:
- **Platform Service**:
  - User authentication (JWT validation)
  - Tenant existence validation
- **Instrument Integration Service** (NEW):
  - Orders (pending test orders that instruments will execute)
  - Result data normalization patterns (for consistency)

### Provides To:
- **Verification Service**:
  - Sample and result data for auto-verification
  - Result updates (verification_status, verification_method)
  - Patient history for delta checks
- **Instrument Integration Service** (NEW):
  - Test orders from LIS (pending work for instruments to execute)
  - Confirmed samples (which samples need test results from instruments)

**Communication Patterns:**
- **With Verification Service:**
  - Reads samples/results via shared database (PostgreSQL)
  - Verification Service updates `verification_status` on results
  - Event-driven (Phase 2): LIS service publishes "NewResultIngested" event → Verification service consumes
- **With Instrument Integration Service:**
  - Shares `Order` model from `shared/models/order.py` (canonical source of truth)
    - LIS Integration: Creates orders from external LIS systems (owner)
    - Instrument Integration: Assigns orders to instruments and tracks execution
  - Order fields: `patient_id`, `test_codes` (JSON array), `priority`, `assigned_instrument_id`, `status`
  - Shares `orders` table in database (LIS owns/writes, Instrument reads/updates assignment)
  - Shares `results` table (both read, Instrument writes from instruments)
  - When Instrument Service receives results, LIS Service is triggered to send them to external LIS (if auto-upload enabled)

---

## Testing Strategy

### Unit Tests
- Test each LIS adapter independently
- Mock external LIS API calls
- Test duplicate detection logic
- Test data normalization
- Test CSV parsing

### Integration Tests
- Test PostgreSQL repositories
- Test sample + results atomic creation
- Test duplicate detection with database
- Test foreign key constraints
- Test multi-tenant isolation at DB level

### API Tests
- Test push endpoint with valid/invalid API keys
- Test CSV file upload and parsing
- Test sample query filters
- Test tenant scoping
- Test error handling for invalid LIS data

### LIS Adapter Tests
- Test mock adapter generates valid data
- Test REST API adapter handles timeouts
- Test file upload adapter rejects malformed CSV
- Test connection health checks

---

## Background Jobs (Pull Model Only)

### Task: PullFromLIS
- **Trigger**: Scheduled based on tenant configuration (default: every 5 minutes)
- **Process**:
  1. Get all tenants with pull model configured
  2. For each tenant:
     - Check if interval elapsed since last pull
     - Call LIS adapter to retrieve new data
     - Process samples and results
     - Update last_successful_retrieval timestamp
     - On failure: increment failure_count, retry with backoff
- **Retry Logic**: Exponential backoff (1 min, 2 min, 4 min)
- **Alert**: Notify admin after 3 consecutive failures

---

## Implementation References

- **Architecture Principles:** [ARCHITECTURE-CORE.md](ARCHITECTURE-CORE.md) - Hexagonal architecture with ports & adapters
- **Multi-Tenancy Patterns:** [ARCHITECTURE-MULTITENANCY.md](ARCHITECTURE-MULTITENANCY.md) - Tenant isolation strategies
- **Service Decomposition:** [PROPOSED-ARCHITECTURE.md](PROPOSED-ARCHITECTURE.md), lines 46-79

---

*This specification details the LIS Integration Service implementation requirements. Refer to [SPECIFICATION.md](SPECIFICATION.md) for system-wide vision, cross-cutting concerns, and success metrics.*
