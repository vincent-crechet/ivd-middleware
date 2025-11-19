# Proposed Data Flow: End-to-End Workflows

This document describes the complete data flow through IVD Middleware, showing how data moves between services in the MVP.

---

## Overview

The system implements an **Instrument → Middleware → Verification → LIS** workflow:

1. **Instruments** query middleware for pending test orders
2. **Instruments** send test results to middleware
3. **Middleware** verifies results (auto-verify or flag for review)
4. **Middleware** uploads verified results back to external **LIS**

---

## Workflow 1: Order Flow (LIS → Instruments)

### Scenario
External LIS sends test orders. Instruments query middleware for pending work. Middleware delivers orders to instruments.

### Data Flow Diagram

```
┌──────────────────┐
│  External LIS    │
│  System          │
└────────┬─────────┘
         │
         │ POST /api/v1/lis/ingest
         │ (LIS sends orders + sample info)
         │
         ▼
┌──────────────────────────────┐
│  LIS Integration Service     │
│  (Receive / Ingest)          │
├──────────────────────────────┤
│ 1. Receive order             │
│ 2. Parse & validate          │
│ 3. Detect duplicates         │
│ 4. Create Sample record      │
│ 5. Create Order record       │
│ 6. Store in PostgreSQL       │
└────────┬─────────────────────┘
         │
         │ Write to database
         │
         ▼
┌──────────────────────────────┐
│  PostgreSQL Database         │
├──────────────────────────────┤
│ samples table:               │
│ - sample_id                  │
│ - external_lis_id            │
│ - patient_id                 │
│ - specimen_type              │
│ - collection_date            │
│                              │
│ orders table:                │
│ - order_id                   │
│ - sample_id (FK)             │
│ - test_codes                 │
│ - status: "pending"          │
└────────┬─────────────────────┘
         │
         │ Query for pending orders
         │
         ▼
┌──────────────────────────────┐
│ Instrument Integration Svc   │
│ (Query / Deliver)            │
├──────────────────────────────┤
│ 1. Receive host query        │
│    POST /query-host          │
│    (patient_id)              │
│ 2. Authenticate with token   │
│ 3. Query pending orders      │
│ 4. Return orders to instr.   │
│ 5. Update order status:      │
│    "in_progress"             │
│ 6. Log query in audit        │
└────────┬─────────────────────┘
         │
         │ Response with pending orders
         │
         ▼
┌──────────────────────────────┐
│  Analytical Instrument       │
│  (e.g., Hematology Analyzer) │
│  RECEIVES PENDING ORDERS     │
└──────────────────────────────┘
```

### Timeline

| Time | Actor | Action | Result |
|------|-------|--------|--------|
| T+0s | External LIS | Sends POST `/api/v1/lis/ingest` with order | Order stored, status="pending" |
| T+1s | Instrument | Sends POST `/api/v1/instruments/query-host` | Returns list of pending orders |
| T+2s | Instrument | Receives response with 5 orders | Instrument loads test program |
| T+3s | Instrument | Processes samples, generates results | Results ready for upload |

### Data Validation

- **Incoming order must have:**
  - Patient identifier (required)
  - Sample barcode or ID (required)
  - List of test codes (required)
  - Collection timestamp (required)

- **Order stored with:**
  - Automatic deduplication: `(external_lis_id, tenant_id)`
  - Default status: "pending"
  - Created timestamp: now
  - Last updated: now

---

## Workflow 2: Result Flow (Instruments → Middleware → Verification → LIS)

### Scenario
Instrument sends test results. Middleware stores and verifies. Verification service auto-verifies or flags for review. Verified results are sent to external LIS.

### Data Flow Diagram (Complete End-to-End)

```
┌──────────────────────────┐
│  Analytical Instrument   │
│  (Results Ready)         │
└────────┬─────────────────┘
         │
         │ POST /api/v1/instruments/results
         │ {
         │   test_code: "GLU",
         │   value: 95.5,
         │   unit: "mg/dL",
         │   reference_range: {low: 70, high: 100},
         │   flags: [],
         │   timestamp: "2024-11-19T08:05:00Z"
         │ }
         │
         ▼
┌──────────────────────────────────┐
│ Instrument Integration Service   │
│ (Receive & Store Results)        │
├──────────────────────────────────┤
│ 1. Receive result from instrument│
│ 2. Authenticate with token       │
│ 3. Validate result format        │
│ 4. Detect duplicates             │
│    (external_result_id, tenant)  │
│ 5. Link to correct sample        │
│ 6. Store in results table        │
│ 7. Mark order status:            │
│    "completed"                   │
│ 8. Return 202 Accepted           │
└────────┬─────────────────────────┘
         │
         │ INSERT into results table
         │
         ▼
┌──────────────────────────────────────┐
│ PostgreSQL - results table           │
├──────────────────────────────────────┤
│ result_id: "550e84xx"                │
│ sample_id: "sample_id_from_lis"      │
│ tenant_id: "tenant_123"              │
│ external_result_id: "LIS_RES_001"    │
│ test_code: "GLU"                     │
│ value: 95.5                          │
│ unit: "mg/dL"                        │
│ reference_range: {low: 70, high: 100}│
│ verification_status: "pending"       │
│ uploaded_to_lis: false               │
│ created_at: now                      │
└────────┬────────────────────────────┘
         │
         │ Database trigger or event
         │ "NewResultIngested"
         │
         ▼
┌──────────────────────────────────┐
│ Verification Service             │
│ (Auto-Verify)                    │
├──────────────────────────────────┤
│ 1. Receive notification of new   │
│    result                        │
│ 2. Load verification settings    │
│    for tenant                    │
│ 3. Apply verification rules:     │
│    - Reference range check       │
│    - Critical range check        │
│    - Instrument flag check       │
│    - Delta check                 │
│ 4. Decision:                     │
│    - PASS: all rules pass        │
│      → status = "verified"       │
│      → method = "auto"           │
│    - FAIL: any rule fails        │
│      → status = "needs_review"   │
│      → add to review queue       │
│ 5. Update result record          │
└────────┬────────────────────────┘
         │
         │ UPDATE results table
         │ verification_status,
         │ verification_method
         │
         ▼
┌──────────────────────────────────────┐
│ PostgreSQL - results table           │
├──────────────────────────────────────┤
│ verification_status: "verified"      │
│ verification_method: "auto"          │
│ verified_at: now                     │
│ (or "needs_review" if failed rules)  │
└────────┬────────────────────────────┘
         │
         │ If auto-verified:
         │ Check auto-upload setting
         │
         ▼
┌──────────────────────────────────┐
│ LIS Integration Service          │
│ (Send Results to External LIS)   │
├──────────────────────────────────┤
│ 1. Check if auto-upload enabled  │
│ 2. Get verified results          │
│ 3. Check upload status for each  │
│    (pending, sent, failed)       │
│ 4. For pending results:          │
│    - Validate LIS connection     │
│    - Batch upload to external    │
│      LIS API                     │
│    - On success:                 │
│      upload_status = "sent"      │
│      sent_to_lis_at = now        │
│    - On failure:                 │
│      upload_status = "failed"    │
│      failure_count++             │
│      schedule retry              │
│ 5. Log upload attempt            │
└────────┬───────────────────────┘
         │
         │ POST to external LIS API
         │ (if auto-upload enabled)
         │
         ▼
┌──────────────────────────────┐
│  External LIS System         │
│  (Receives Verified Results) │
│  UPLOAD COMPLETE             │
└──────────────────────────────┘
```

### Scenario A: Result Auto-Verified (Happy Path)

```
Instrument sends result
         │
         ▼
Middleware stores result
         │
         ▼
Verification Service auto-verifies
(all rules pass)
         │
         ▼
Result marked "verified"
         │
         ▼
LIS Integration Service sends to LIS
(if auto-upload enabled)
         │
         ▼
External LIS receives verified result
```

**Duration:** ~1-2 seconds (end-to-end)

### Scenario B: Result Needs Review (Exception Path)

```
Instrument sends result
         │
         ▼
Middleware stores result
         │
         ▼
Verification Service evaluates
(delta check fails: value changed 50%)
         │
         ▼
Result marked "needs_review"
         │
         ▼
Added to review queue for lab technician
         │
         ▼
Lab technician reviews result
         │
         ├─ APPROVE
         │  │
         │  ▼
         │  Result marked "verified"
         │  │
         │  ▼
         │  LIS Integration sends to LIS
         │
         └─ REJECT
            │
            ▼
            Result marked "rejected"
            │
            ▼
            Escalated to pathologist
```

**Duration:** ~5-30 minutes (includes human review)

---

## Workflow 3: Manual Review Process

### Scenario
Result failed auto-verification and needs manual review.

### Data Flow

```
Review Queue (Samples with flagged results)
    │
    ▼
Lab Technician views review queue
    │
    ├─ Selects sample
    │  │
    │  ▼
    │  View all results for sample
    │  (auto-verified + flagged)
    │  │
    │  ├─ APPROVE (all results are valid)
    │  │  │
    │  │  ▼
    │  │  Update all "needs_review" → "verified"
    │  │  Set verification_method = "manual"
    │  │  Set verified_at = now
    │  │  Set reviewer_id = current_user
    │  │  │
    │  │  ▼
    │  │  LIS Integration uploads to LIS
    │  │
    │  ├─ REJECT (results are invalid)
    │  │  │
    │  │  ▼
    │  │  Update results → "rejected"
    │  │  Set verification_method = "manual"
    │  │  Require comment from technician
    │  │  DO NOT send to LIS
    │  │
    │  └─ ESCALATE (need pathologist opinion)
    │     │
    │     ▼
    │     Mark "escalated"
    │     Send to pathologist queue
    │     │
    │     ▼
    │     Pathologist reviews
    │     (Same approve/reject options)
    │
    └─ Sample removed from queue once all results are reviewed
```

---

## Workflow 4: Bidirectional LIS Communication

### Scenario
LIS connection is configured for bidirectional communication.

### Data Flow (Complete Loop)

```
INBOUND (Order from LIS):
External LIS
    │
    └──> POST /api/v1/lis/ingest
         │
         ▼
    Store in orders + samples table
         │
         ▼
    (Instrument queries for orders)

INSTRUMENT PROCESSING:
Instrument
    │
    ├──> POST /api/v1/instruments/query-host
    │    │
    │    └──> Return pending orders
    │
    └──> POST /api/v1/instruments/results
         │
         ▼
         Store results in results table

VERIFICATION:
Verification Service
    │
    ├──> Auto-verify results
    │    │
    │    └──> Mark "verified" or "needs_review"
    │
    └──> Trigger manual review if needed

OUTBOUND (Result to LIS):
LIS Integration Service
    │
    └──> POST to external LIS API
         (send verified results)
         │
         ▼
    External LIS receives results
         │
         ▼
    Cycle complete!
```

---

## Data Consistency & ACID Guarantees

### Transaction Boundaries

**Per-Result Transaction:**
1. Receive result from instrument
2. Validate format
3. Check for duplicates
4. Store in database
5. Commit or rollback

**Result Verification Transaction:**
1. Read result
2. Load verification settings
3. Apply rules
4. Update verification status
5. Commit

**Result Upload Transaction:**
1. Get unupload results
2. Call external LIS API
3. Update upload_status on success
4. Commit

### Idempotency

- **Duplicate detection:** If instrument resends same result ID, second attempt is silently skipped
- **Upload retry:** If upload fails and retried, idempotent operation (same effect as first attempt)
- **Verification:** Idempotent - running verification multiple times produces same result

### Eventual Consistency

- Instruments may submit results multiple times
- Duplicates are detected and skipped
- Verification is eventually consistent (all results verified or flagged)
- Upload to LIS may be delayed (retries with backoff)

---

## Error Handling

### Common Error Scenarios

**1. Instrument sends malformed result:**
```
POST /api/v1/instruments/results
{
  "test_code": "GLU",
  "value": "not_a_number"  ← INVALID
}
```
→ Response: 400 Bad Request with error details
→ Result NOT stored
→ Instrument can retry

**2. Duplicate result detected:**
```
POST /api/v1/instruments/results
(same external_result_id as before)
```
→ Response: 202 Accepted (idempotent)
→ Result NOT stored again
→ No error

**3. LIS connection fails during upload:**
```
LIS API unreachable
```
→ Upload marked "failed"
→ Failure count incremented
→ Retry scheduled (exponential backoff: 1 min, 2 min, 4 min, 8 min)
→ Admin notified after 3 consecutive failures

---

## Performance Characteristics

| Operation | Target | Notes |
|-----------|--------|-------|
| Order ingestion | < 500ms | Parse, validate, store order |
| Instrument query response | < 500ms | Return pending orders list |
| Result ingestion | < 1s | Store, trigger verification |
| Auto-verification | < 1s per result | Apply 4 rule checks |
| Manual review | ~5-30 min | Human decision time |
| Upload to LIS | < 5s per batch | API call + confirm |
| Retry mechanism | Exponential backoff | 1, 2, 4, 8 minutes |

---

## Multi-Tenancy Data Isolation

All data flows respect tenant boundaries:

```
Instrument queries:
    ├─ Authenticate instrument API token
    ├─ Extract tenant_id from token
    └─ Return ONLY orders for that tenant

Result storage:
    ├─ Store tenant_id with every result
    └─ Database enforces (external_result_id, tenant_id) uniqueness

LIS upload:
    ├─ Fetch LIS configuration for tenant
    ├─ Send results for that tenant only
    └─ Never cross-tenant data exposure
```

---

## Key Design Principles

1. **Loose Coupling:** Services communicate via shared database or events, not direct API calls
2. **Idempotency:** Operations can be safely retried without side effects
3. **Immutability:** Verified/rejected results cannot be modified
4. **Audit Trail:** All operations logged with timestamp and user
5. **Multi-tenant Safety:** Tenant_id enforced at database and application layer

---

*This data flow document describes how the IVD Middleware processes data from instruments, through verification, and back to the LIS, demonstrating the complete end-to-end MVP workflow.*
