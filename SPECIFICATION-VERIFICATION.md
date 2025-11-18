# Verification & Review Service - Specification

*Part of IVD Middleware. See [SPECIFICATION.md](SPECIFICATION.md) for system overview, cross-cutting concerns, and global non-functional requirements.*

---

## Service Responsibility

The Verification & Review Service implements the core business logic for laboratory result verification. It handles:

- **Auto-Verification Settings**: Configure reference ranges, critical ranges, and instrument flags per test
- **Automated Result Verification**: Apply configurable rules to auto-verify or flag results
- **Manual Review Workflow**: Route flagged results to qualified staff for decision-making
- **Review Queue Management**: Track samples requiring human review
- **Escalation Workflow**: Enable technicians to escalate complex cases to pathologists
- **Audit Trail**: Maintain complete history of all verification decisions

**Service Boundary:** All verification logic, review workflows, and verification settings are owned by this service.

---

## Features

### Feature 5: Automated Result Verification

**What It Does:**
Automatically evaluates each result against configurable rules. Results passing all rules are verified; results failing any rule are flagged for manual review.

**User Stories:**

1. **As a laboratory administrator**, I want to define verification rules so that results are evaluated according to our laboratory's standards.

2. **As a lab technician**, I want routine normal results to be auto-verified so that I only review exceptions.

3. **As a pathologist**, I want critical results to always require human review so that we don't miss important findings.

**Requirements:**
- Evaluate each result immediately after ingestion
- Support these verification rule types:
  - **Reference Range Check**: Value within configured normal range?
  - **Critical Range Check**: Value within critical threshold?
  - **Instrument Flag Check**: Result has instrument flag requiring manual review?
  - **Delta Check**: Value changed significantly from patient's previous result?
- Rules are configurable per laboratory via auto-verification settings
- Laboratory admin can enable/disable each rule type
- Laboratory admin can configure rule parameters (ranges, thresholds, flags)

**Acceptance Criteria:**
- [ ] New results are automatically evaluated against all active rules
- [ ] If all rules pass, result is marked "verified"
- [ ] If any rule fails, result is marked "needs_review"
- [ ] Results marked "needs_review" appear in review queue (sample level)
- [ ] Lab admin can configure reference ranges per test in auto-verification settings
- [ ] Lab admin can configure critical ranges per test in auto-verification settings
- [ ] Lab admin can configure list of instrument flags that prevent auto-verification
- [ ] Lab admin can enable or disable each rule type
- [ ] Lab admin can modify delta check thresholds (percentage change)
- [ ] Reference ranges are stored in system settings (not from LIS data)
- [ ] Critical determination is based on configured critical ranges (not LIS flags)

**Business Rules:**
- ALL active rules must pass for auto-verification
- If ANY active rule fails, result requires manual review
- Rules apply only to the tenant that defined them
- New tenants start with default rules and ranges
- Reference ranges and critical ranges are configured per test code
- If no range is configured for a test, that test cannot be auto-verified
- Instrument flags list can include: "H" (high), "L" (low), "C" (critical), or custom flags
- Delta checks only apply if patient has previous result for same test

**Verification Rule Details:**

#### Reference Range Check
- Compares result value to configured normal reference range (low/high bounds)
- Reference ranges are defined in auto-verification settings per test code
- **Pass**: Value is within configured range
- **Fail**: Value is outside configured range

#### Critical Range Check
- Compares result value to configured critical thresholds
- Critical ranges are defined in auto-verification settings per test code
- **Pass**: Value is not in critical range
- **Fail**: Value is in critical range (too high or too low)

#### Instrument Flag Check
- Checks if result has an instrument flag from the configured "do not auto-verify" list
- Laboratory defines which instrument flags prevent auto-verification
- **Pass**: Result has no flags OR result's flag is not in the "do not auto-verify" list
- **Fail**: Result has a flag that is in the "do not auto-verify" list

#### Delta Check
- Compares current value to patient's most recent previous value for same test
- **Pass**: Change is less than configured threshold (e.g., <10%)
- **Fail**: Change exceeds configured threshold
- Only evaluated if previous result exists and is recent enough (e.g., within last 30 days)

---

### Feature 6: Manual Review Workflow

**What It Does:**
Routes samples with results that failed auto-verification to qualified staff for decision-making. Reviews are performed at the sample level, covering all non-auto-verified results for that sample. Captures decisions and reasoning for audit trail.

**User Stories:**

1. **As a lab technician**, I want to see all samples that need review so that I can process them efficiently.

2. **As a lab technician**, I want to see which results in a sample were flagged and why so that I can make an informed decision.

3. **As a lab technician**, I want to review all results for a sample together so that I have complete context.

4. **As a lab technician**, I want to escalate complex cases to a pathologist so that a medical expert can decide.

5. **As a pathologist**, I want to see escalated samples with full context so that I can provide clinical judgment.

**Requirements:**
- Maintain a review queue of samples needing manual review
- A sample appears in the queue if at least one result has not been auto-verified
- Show reviewers which results in the sample were flagged and why
- Allow reviewers to review all results in a sample together
- Allow reviewers to approve or reject individual results or the entire sample
- Allow reviewers to escalate samples to pathologists
- Capture decision reasoning in comments
- Maintain audit trail of all review decisions

**Review States:**
- **Pending** - Sample awaiting assignment
- **In Progress** - Sample assigned to a reviewer
- **Approved** - Reviewer confirmed all results are valid
- **Rejected** - Reviewer determined one or more results are invalid
- **Escalated** - Sent to pathologist for expert review

**Acceptance Criteria:**
- [ ] Review queue shows all samples with at least one result marked "needs_review"
- [ ] Each queue entry shows: sample ID, patient ID, collection date, number of flagged results
- [ ] Reviewer can select a sample to review
- [ ] Review screen shows all results for the sample (both auto-verified and flagged)
- [ ] Flagged results are clearly marked with reason (which rule failed)
- [ ] Review screen shows patient's previous results for same tests
- [ ] Reviewer can approve entire sample (marks all flagged results as "verified")
- [ ] Reviewer can approve/reject individual results with comments
- [ ] Reviewer can reject entire sample with mandatory comment
- [ ] Technician can escalate sample to pathologist with mandatory reason
- [ ] Approving results marks them as "verified"
- [ ] Rejecting results marks them as "rejected"
- [ ] Escalated samples appear in pathologist's queue
- [ ] Completed reviews are locked (cannot be modified)
- [ ] All decisions are timestamped and attributed to reviewer
- [ ] Sample is removed from queue when all flagged results are reviewed

**Business Rules:**
- Each sample can have only one active review at a time
- A sample appears in review queue if ANY of its results need review
- Comments are mandatory for rejections
- Comments are optional for approvals
- Escalation reason is mandatory
- Once a review is submitted for a result, that result's review decision cannot be changed
- Reviewers can only review samples for their own laboratory
- Only technicians and pathologists can perform reviews
- Escalated reviews can only be completed by pathologists
- Auto-verified results in a sample do not need review (but are visible for context)

---

### Feature 7 (Partial): Sample & Result Querying - Verification Context

**What It Does:**
Provides verification and review context when viewing samples and results.

**Requirements:**
- Display verification status on each result (pending, verified, needs_review, rejected)
- Show verification method (auto-verified, manually reviewed)
- Show review history with reviewer identity and decisions
- Show which verification rules failed (for flagged results)

**Acceptance Criteria:**
- [ ] For verified results, show whether auto-verified or manually reviewed
- [ ] For manually reviewed results, show reviewer name, decision, and comments
- [ ] For flagged results, show which rule(s) failed
- [ ] Display complete audit trail of verification decisions

**Note:** Base sample/result querying and filtering is provided by the LIS Integration Service. This service adds verification-specific metadata.

---

## Data Entities Owned

### Review
A decision record for a sample with results that failed auto-verification. Reviews are performed at the sample level, covering all non-auto-verified results.

**Key Attributes:**
- Unique identifier (UUID)
- Sample ID (foreign key, NOT NULL)
- Tenant ID (foreign key, NOT NULL)
- Reviewer user ID (foreign key)
- Review state (pending, in_progress, approved, rejected, escalated)
- Decision (approve_all, reject_all, partial)
- Comments (mandatory for rejections, optional for approvals)
- Escalation reason (mandatory if state = escalated)
- Timestamps (created_at, submitted_at, completed_at)

**Key Relationships:**
- Each review is associated with exactly one sample
- Each review belongs to exactly one tenant
- One review has many result decisions (one per flagged result)

---

### Result Decision (Sub-entity of Review)
Individual decision for each result in a sample review.

**Key Attributes:**
- Review ID (foreign key, NOT NULL)
- Result ID (foreign key, NOT NULL)
- Decision (approved, rejected)
- Comments (text)
- Timestamp (decided_at)

**Immutability:**
- Once submitted, result decisions cannot be changed

---

### Verification Rule
Defines how results should be automatically evaluated for a laboratory. Rules are configurable per tenant.

**Key Attributes:**
- Tenant ID (foreign key, NOT NULL)
- Rule type (reference_range, critical_range, instrument_flag, delta_check)
- Enabled (boolean)
- Priority (integer, for rule evaluation order)

**Note:** Verification rules are metadata. Actual parameters (ranges, flags, thresholds) are in Auto-Verification Settings.

---

### Auto-Verification Settings
Configuration that defines reference ranges, critical ranges, and instrument flags for automatic result verification. Configured per tenant and per test code.

**Key Attributes:**
- Unique identifier (UUID)
- Tenant ID (foreign key, NOT NULL)
- Test code (e.g., "GLU" for glucose)
- Test name (e.g., "Glucose")
- Reference range low (numeric, nullable)
- Reference range high (numeric, nullable)
- Critical range low (numeric, nullable)
- Critical range high (numeric, nullable)
- Instrument flags to block (JSON array, e.g., ["H", "L", "C"])
- Delta check threshold percentage (numeric, nullable)
- Delta check lookback days (integer, default: 30)
- Timestamps (created_at, updated_at)

**Composite Unique Constraint:** (tenant_id, test_code)

---

## API Endpoints

Based on [PROPOSED-ARCHITECTURE.md](PROPOSED-ARCHITECTURE.md), the Verification & Review Service exposes:

### Auto-Verification Settings Management
- `GET /api/v1/verification/settings` - List verification settings for tenant
- `GET /api/v1/verification/settings/{test_code}` - Get settings for specific test
- `POST /api/v1/verification/settings` - Create/update settings for test (admin only)
- `PUT /api/v1/verification/settings/{test_code}` - Update settings (admin only)
- `DELETE /api/v1/verification/settings/{test_code}` - Delete settings (admin only)

### Verification Rules Configuration
- `GET /api/v1/verification/rules` - List all rules for tenant with enabled status
- `PUT /api/v1/verification/rules` - Enable/disable rule types (admin only)

### Review Queue & Workflow
- `GET /api/v1/reviews/queue` - Get review queue for tenant (techs and pathologists only)
  - Filter: `assigned_to_me`, `escalated` (for pathologists)
- `GET /api/v1/reviews/{sample_id}` - Get review details for a sample
- `POST /api/v1/reviews` - Create review for sample (assigns to current user)
- `POST /api/v1/reviews/{id}/approve` - Approve entire sample
- `POST /api/v1/reviews/{id}/reject` - Reject entire sample with comment
- `POST /api/v1/reviews/{id}/approve-result` - Approve individual result
- `POST /api/v1/reviews/{id}/reject-result` - Reject individual result with comment
- `POST /api/v1/reviews/{id}/escalate` - Escalate to pathologist with reason

### Verification History
- `GET /api/v1/results/{id}/verification-history` - Get complete audit trail for result
- `GET /api/v1/samples/{id}/review-history` - Get review history for sample

---

## Multi-Tenancy Implementation

1. **Tenant Scoping:**
   - All reviews, verification rules, and settings have `tenant_id` foreign key
   - All queries automatically filter by `tenant_id` from JWT
   - Verification settings are unique per (tenant_id, test_code)

2. **Data Isolation:**
   - Composite unique index: (tenant_id, test_code) for auto-verification settings
   - Reviews scoped to tenant samples only
   - No cross-tenant verification data access

3. **Rule Isolation:**
   - Each tenant has independent verification rules
   - Default rules initialized on tenant creation
   - Rule changes do not affect other tenants

---

## Cross-Cutting Concerns (Service-Specific)

### Multi-Tenancy
- All verification logic scoped to tenant settings
- Review queue shows only tenant's samples
- Audit trail includes tenant context

### Authentication & Authorization
- Validates JWT tokens via Platform Service
- Role-based access:
  - Admin: Manage verification settings and rules
  - Technician: Perform reviews, escalate to pathologist
  - Pathologist: Perform reviews, handle escalations

### Audit Trail & Compliance
- All review decisions logged with timestamp and user
- All escalations logged with reason
- Verified/rejected results are immutable
- Complete history maintained for regulatory compliance

### Data Integrity
- Reviews must reference valid samples
- Result decisions must reference valid results
- Foreign key constraints enforced
- Immutability enforced: completed reviews cannot be modified

---

## Non-Functional Requirements (Service-Specific)

### Performance
- Auto-verification completes within 1 second per result
- Review queue loads within 2 seconds
- Verification rule evaluation < 100ms per result
- Support verification of 1000+ results in batch

### Scalability
- Horizontal scaling via stateless design
- Event-driven verification (listen to NewResultIngested events)
- Database indexing on: (tenant_id, sample_id, verification_status)
- Support at least 50,000 results per tenant

### Reliability
- Verification logic is idempotent (safe to run multiple times)
- Failed verification retries automatically
- No data loss on system restart
- Graceful degradation if verification temporarily unavailable

### Security
- Audit trail includes user identity for all decisions
- Role-based access enforced at API level
- Comments cannot contain PHI (logged warning if detected)
- Immutable audit trail prevents tampering

---

## Verification Engine Architecture

### Event-Driven Verification

**Flow:**
1. LIS Integration Service ingests new result
2. LIS service publishes `NewResultIngested` event to message queue
3. Verification Service consumes event
4. Verification Engine applies all active rules for tenant
5. Update result `verification_status` and `verification_method`
6. If needs_review: Add sample to review queue (if not already there)

**Rule Evaluation Order:**
1. Reference Range Check
2. Critical Range Check
3. Instrument Flag Check
4. Delta Check (requires patient history lookup)

**Short-Circuit:**
- If ANY rule fails, immediately mark as needs_review (no need to evaluate remaining rules)

---

## Integration with Other Services

### Depends On:
- **Platform Service**:
  - User authentication (JWT validation)
  - Tenant existence validation
  - User identity for review attribution

- **LIS Integration Service**:
  - Sample and result data (read access)
  - Result update (write verification_status)
  - Patient history for delta checks

**Communication:**
- Reads samples/results via shared database (PostgreSQL)
- Updates `verification_status`, `verification_method`, `verified_at` on results
- Event-driven: Consumes `NewResultIngested` event from LIS service

### Provides To:
- **Web Applications**:
  - Review queue for technicians/pathologists
  - Verification settings management UI
  - Audit trail and compliance reporting

---

## Testing Strategy

### Unit Tests
- Test each verification rule independently
- Mock result data and settings
- Test rule pass/fail logic
- Test delta check calculation
- Test review decision validation

### Integration Tests
- Test verification engine with real database
- Test event consumption
- Test review workflow end-to-end
- Test audit trail persistence
- Test immutability enforcement

### API Tests
- Test verification settings CRUD
- Test review queue filtering
- Test review submission and approval/rejection
- Test escalation workflow
- Test role-based access control

### Rule Tests
- Test reference range edge cases (boundary values)
- Test critical range detection
- Test instrument flag matching
- Test delta check with/without previous result
- Test rule combinations

---

## Default Verification Settings (Initial Tenant Setup)

When a new tenant is created, initialize with these default auto-verification settings:

| Test Code | Test Name | Ref Range Low | Ref Range High | Critical Low | Critical High | Flags to Block |
|-----------|-----------|---------------|----------------|--------------|---------------|----------------|
| GLU | Glucose | 70 | 100 | 40 | 400 | ["C"] |
| WBC | White Blood Count | 4.5 | 11.0 | 2.0 | 30.0 | ["C"] |
| HGB | Hemoglobin | 12.0 | 16.0 | 7.0 | 20.0 | ["C"] |
| PLT | Platelets | 150 | 400 | 50 | 1000 | ["C"] |
| NA | Sodium | 136 | 145 | 120 | 160 | ["C"] |
| K | Potassium | 3.5 | 5.0 | 2.5 | 6.5 | ["C", "H", "L"] |

**Default Rule Enablement:**
- Reference Range Check: Enabled
- Critical Range Check: Enabled
- Instrument Flag Check: Enabled
- Delta Check: Disabled (can be enabled by admin)

---

## Implementation References

- **Architecture Principles:** [ARCHITECTURE-CORE.md](ARCHITECTURE-CORE.md) - Hexagonal architecture with ports & adapters
- **Multi-Tenancy Patterns:** [ARCHITECTURE-MULTITENANCY.md](ARCHITECTURE-MULTITENANCY.md) - Tenant isolation strategies
- **Service Decomposition:** [PROPOSED-ARCHITECTURE.md](PROPOSED-ARCHITECTURE.md), lines 81-118

---

*This specification details the Verification & Review Service implementation requirements. Refer to [SPECIFICATION.md](SPECIFICATION.md) for system-wide vision, cross-cutting concerns, and success metrics.*
