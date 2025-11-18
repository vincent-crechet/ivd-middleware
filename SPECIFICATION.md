# IVD Middleware - Product Specification (Master)

This document defines **what** the IVD Middleware should do from a functional and business perspective. It focuses on user needs, features, and requirements without prescribing technical implementation details.

**Note:** This is the master specification containing system-wide vision, cross-cutting concerns, and global non-functional requirements. For service-specific implementation details, see:
- **[SPECIFICATION-PLATFORM.md](SPECIFICATION-PLATFORM.md)** - Platform Service (Features 1-2)
- **[SPECIFICATION-LIS-INTEGRATION.md](SPECIFICATION-LIS-INTEGRATION.md)** - LIS Integration Service (Features 3-4)
- **[SPECIFICATION-VERIFICATION.md](SPECIFICATION-VERIFICATION.md)** - Verification & Review Service (Features 5-7)

---

## 1. Product Vision

### Purpose
IVD Middleware is a multi-tenant platform that automates laboratory result verification and management. It connects to Laboratory Information Systems (LIS), applies configurable validation rules, and routes exceptions to qualified staff for review.

### Problem Being Solved
Laboratory result verification is time-consuming and error-prone when done manually. Different LIS systems produce results in varying formats. Results must be validated against reference ranges, patient history, and critical value thresholds before clinical use.

### Success Criteria
- Reduce manual verification workload by 70%+ through automation
- Ensure zero data leakage between tenants (laboratories)
- Maintain complete audit trail for all verification decisions
- Support at least 10 concurrent laboratory tenants

### MVP Scope
**In Scope:**
- Multi-tenant architecture with complete data isolation
- User authentication and role-based access
- LIS integration (mock data, file upload, REST API)
- Automated result verification with configurable rules
- Manual review workflow for flagged results
- Sample and result querying

**Out of Scope (Future Phases):**
- Advanced analytics and dashboards
- Mobile applications
- HL7 message handling
- EHR system integration
- Direct instrument connections

---

## 2. Users & Their Goals

### Laboratory Administrator
**Who:** Person responsible for laboratory operations and system configuration

**Goals:**
- Set up new laboratory tenant in the system
- Manage user accounts and assign appropriate roles
- Configure how the laboratory's LIS connects to the middleware
- Define verification rules appropriate for the laboratory's workflow
- Monitor system health and review activity

**Key Capabilities Needed:**
- Create and configure laboratory tenant settings
- Add/remove users and assign roles
- Configure LIS connection parameters
- View all samples, results, and reviews for their laboratory
- Customize verification rules and thresholds

### Lab Technician
**Who:** Laboratory staff member who processes routine results

**Goals:**
- Quickly review results that didn't auto-verify
- Understand why each result was flagged
- Make approve/reject decisions efficiently
- Track personal review history

**Key Capabilities Needed:**
- View samples and results for their laboratory
- Access review queue showing unreviewed results
- Approve or reject results with comments
- Escalate complex cases to pathologists
- See patient history for context

### Pathologist / Senior Reviewer
**Who:** Medical doctor who handles complex or escalated cases

**Goals:**
- Review medically complex or escalated results
- Provide clinical justification for decisions
- Ensure review quality and accuracy

**Key Capabilities Needed:**
- View all samples and results
- Receive and process escalated reviews
- Approve/reject with detailed clinical comments
- Review other staff members' decisions

---

## 3. Features & Requirements

The IVD Middleware features are organized by service boundary. Detailed requirements, acceptance criteria, and business rules are documented in service-specific specifications.

### Features Summary & Service Mapping

#### Platform Service Features
See [SPECIFICATION-PLATFORM.md](SPECIFICATION-PLATFORM.md) for complete details.

**Feature 1: Tenant Management**
- Create and manage isolated laboratory organizations (tenants)
- Data segregation and multi-tenancy enforcement
- Tenant activation/deactivation
- Atomic tenant creation with first admin user

**Feature 2: User & Access Management**
- User accounts with role-based access control (Admin, Technician, Pathologist)
- Secure authentication with JWT tokens containing tenant context
- Session management and password security
- Role-based authorization

---

#### LIS Integration Service Features
See [SPECIFICATION-LIS-INTEGRATION.md](SPECIFICATION-LIS-INTEGRATION.md) for complete details.

**Feature 3: Sample & Result Ingestion**
- Retrieve laboratory samples and test results from external LIS systems
- Data normalization and duplicate detection
- Support searching and filtering of samples

**Feature 4: LIS Integration**
- Connect to external Laboratory Information Systems
- Support both push (LIS sends data) and pull (middleware retrieves) models
- Multiple LIS adapters (mock, file upload, REST API)
- Connection health monitoring and error handling

---

#### Verification & Review Service Features
See [SPECIFICATION-VERIFICATION.md](SPECIFICATION-VERIFICATION.md) for complete details.

**Feature 5: Automated Result Verification**
- Auto-verify results using configurable rules
- Reference range check, critical range check, instrument flag check, delta check
- Per-tenant configuration of verification settings

**Feature 6: Manual Review Workflow**
- Route flagged results to qualified staff for review
- Sample-level reviews with complete context
- Escalation workflow from technicians to pathologists
- Complete audit trail of all decisions

**Feature 7: Sample & Result Querying**
- Search and filter samples by patient, date, status
- View results with verification status and review history
- Compliance reporting and audit trail access

---

### Original Feature Details (Deprecated - See Service Specs)

The detailed feature requirements below have been moved to service-specific specifications. This section is retained for reference but may be out of sync. **Always refer to service-specific specifications for current requirements.**

<details>
<summary>Click to expand legacy feature details (deprecated)</summary>

### Legacy Feature 1: Tenant Management

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

**Reference Range Check:**
- Compares result value to configured normal reference range (low/high bounds)
- Reference ranges are defined in auto-verification settings per test code
- Pass: Value is within configured range
- Fail: Value is outside configured range

**Critical Range Check:**
- Compares result value to configured critical thresholds
- Critical ranges are defined in auto-verification settings per test code
- Pass: Value is not in critical range
- Fail: Value is in critical range (too high or too low)

**Instrument Flag Check:**
- Checks if result has an instrument flag from the configured "do not auto-verify" list
- Laboratory defines which instrument flags prevent auto-verification
- Pass: Result has no flags OR result's flag is not in the "do not auto-verify" list
- Fail: Result has a flag that is in the "do not auto-verify" list

**Delta Check:**
- Compares current value to patient's most recent previous value for same test
- Pass: Change is less than configured threshold (e.g., <10%)
- Fail: Change exceeds configured threshold
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

### Feature 7: Sample & Result Querying

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

---

</details>

---

## 4. Data Entities (Business View)

Data entities are owned by specific services. See service-specific specifications for detailed entity definitions:
- **Platform Service:** Tenant, User → [SPECIFICATION-PLATFORM.md](SPECIFICATION-PLATFORM.md)
- **LIS Integration Service:** Sample, Result, LIS Configuration → [SPECIFICATION-LIS-INTEGRATION.md](SPECIFICATION-LIS-INTEGRATION.md)
- **Verification Service:** Review, Verification Rule, Auto-Verification Settings → [SPECIFICATION-VERIFICATION.md](SPECIFICATION-VERIFICATION.md)

### Entity Relationships Summary

### Tenant
Represents a laboratory or organization. Each tenant operates independently with complete data isolation.

### User
A person with access to the system. Belongs to exactly one tenant. Has a role that determines permissions.

### Sample
A physical specimen submitted to the laboratory for testing. Contains patient identification and specimen details.

### Result
The analytical outcome of a test performed on a sample. Includes measured value, reference range, and verification status.

### Review
A decision record for a sample with results that failed auto-verification. Reviews are performed at the sample level, covering all non-auto-verified results. Documents who reviewed it, their decisions for each result, and reasoning.

### Verification Rule
Defines how results should be automatically evaluated for a laboratory. Rules are configurable per tenant.

### Auto-Verification Settings
Configuration that defines reference ranges, critical ranges, and instrument flags for automatic result verification. Configured per tenant and per test code.

**Key Relationships:**
- Each user, sample, result, and review belongs to exactly one tenant
- Each result belongs to exactly one sample
- Each review is associated with exactly one sample (not individual results)
- A sample may have multiple results, some auto-verified and some requiring review
- Each tenant can have multiple verification rules
- Each tenant has auto-verification settings that define ranges and flags per test code

---

## 5. Cross-Cutting Business Rules

### Multi-Tenancy
- Every data record (except tenants themselves) belongs to exactly one tenant
- Users can only access data for their own tenant
- No data is shared between tenants
- Queries automatically filter by tenant

### Authentication & Authorization
- Users must authenticate before accessing the system
- Authentication tokens include user identity, tenant, and role
- All requests must include valid authentication token
- Actions are authorized based on user role

### Audit Trail & Compliance
- All review decisions must be logged with timestamp and user
- All escalations must be logged with reason
- Verified results cannot be modified (immutable)
- Rejected results cannot be modified (immutable)
- System maintains complete history of all verification decisions

### Data Integrity
- Results cannot be duplicated (duplicate prevention)
- All data changes are transactional (all-or-nothing)
- Foreign key relationships are enforced
- Results must reference valid samples
- Reviews must reference valid results

### Error Handling
- All errors must be logged with sufficient detail for debugging
- User-facing error messages must be clear and actionable
- System errors should not expose sensitive information
- LIS connection failures must be handled gracefully without data loss

---

## 6. Non-Functional Requirements

### Performance
- LIS retrieval completes within 5 minutes for up to 1000 new results
- Auto-verification completes within 1 second per result
- Review queue loads within 2 seconds
- Search/filter operations complete within 2 seconds
- Support 50+ concurrent users per tenant

### Scalability
- Support at least 10 laboratory tenants per deployment
- Support at least 10,000 samples per tenant
- Support at least 50,000 results per tenant
- System performance does not degrade as data grows

### Reliability
- System must handle LIS connection failures gracefully
- Failed LIS retrievals must retry automatically
- No data loss on system restart or failure
- Verification logic is idempotent (safe to run multiple times)

### Security
- Passwords must be hashed using industry-standard algorithm
- LIS connection credentials must be encrypted at rest
- Authentication tokens must expire after reasonable time period
- Role-based access control must be enforced at all layers
- Passwords must never be logged or displayed

### Usability
- Error messages must be clear and actionable
- System must provide feedback on long-running operations
- Review queue must highlight urgent items
- Response times must feel fast to users (<2 seconds for most operations)

---

## 7. Feature Priorities

Features are prioritized across all services. See service-specific specifications for implementation details.

### P0 - Must Have (MVP)

**Platform Service** ([SPECIFICATION-PLATFORM.md](SPECIFICATION-PLATFORM.md)):
- Tenant management (create tenant with first admin user)
- User management (create, authenticate, assign roles)

**LIS Integration Service** ([SPECIFICATION-LIS-INTEGRATION.md](SPECIFICATION-LIS-INTEGRATION.md)):
- Basic LIS integration (mock adapter for testing)
- LIS API endpoint to receive incoming orders (push model)
- Sample and result ingestion
- Sample/result querying (search, filter, view)

**Verification Service** ([SPECIFICATION-VERIFICATION.md](SPECIFICATION-VERIFICATION.md)):
- Auto-verification settings configuration (reference ranges, critical ranges, instrument flags per test)
- Automated verification (reference range, critical range, instrument flag, delta checks)
- Manual review workflow at sample level (approve/reject)

### P1 - Should Have (Phase 1)
- File upload LIS adapter (CSV import)
- REST API pull model (middleware retrieves from LIS)
- Review escalation workflow
- Patient history view in review screen
- LIS connection testing and health monitoring
- Bulk sample review operations

### P2 - Nice to Have (Phase 2)
- Advanced search and filtering
- Bulk operations (approve multiple results)
- Custom verification rules
- Email notifications for critical results
- Review analytics and reporting
- User activity logging

### P3 - Future
- HL7 message handling
- EHR system integration
- Mobile applications
- Advanced dashboards
- Real-time push notifications
- Reflex testing support

---

## 8. Assumptions & Constraints

### Assumptions
- LIS systems provide reference ranges with result data
- LIS systems flag critical results appropriately
- Users have basic computer literacy
- Internet connectivity is reliable
- Laboratories have technical staff to configure LIS connections

### Constraints
- Must maintain HIPAA compliance for patient data
- Must maintain audit trail for regulatory compliance
- Must support laboratories with different LIS vendors
- Initial release targets small to medium laboratories (up to 50 users per tenant)

### Known Limitations (MVP)
- No real-time notifications (users must refresh to see new data)
- No advanced analytics or reporting
- Limited to three user roles (no fine-grained permissions)
- No mobile-optimized interface
- English language only

---

## 9. Success Metrics

The product is successful if it achieves:

- **Automation Rate**: 70%+ of results auto-verified (don't require manual review)
- **Review Time**: Average review decision time <60 seconds per result
- **Zero Data Leaks**: No cross-tenant data access incidents
- **Uptime**: 99%+ system availability
- **User Adoption**: 80%+ of laboratory staff actively using the system within 30 days
- **Error Rate**: <1% of results incorrectly verified (false positives/negatives)

---

## Service-Specific Specifications

For detailed implementation requirements, refer to:

- **[SPECIFICATION-PLATFORM.md](SPECIFICATION-PLATFORM.md)** - Platform Service (Tenant & User Management, Authentication)
- **[SPECIFICATION-LIS-INTEGRATION.md](SPECIFICATION-LIS-INTEGRATION.md)** - LIS Integration Service (Sample/Result Ingestion, LIS Adapters)
- **[SPECIFICATION-VERIFICATION.md](SPECIFICATION-VERIFICATION.md)** - Verification & Review Service (Auto-Verification, Manual Review)

---

*This master specification defines what the IVD Middleware should do from a business and functional perspective. It should be used in conjunction with the service-specific specifications and Architecture documents to guide implementation.*
