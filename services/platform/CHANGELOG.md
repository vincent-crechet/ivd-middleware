# Platform Service - Changelog

## Improvements Made

### 1. **Added Composite Unique Constraint on User Email**
- **Issue**: Email wasn't properly unique per tenant in database
- **Fix**: Added composite unique index on (email, tenant_id) in User model
- **Impact**: Prevents duplicate emails within same tenant at database level

### 2. **Fixed Pydantic v2 Compatibility**
- **Issue**: Using deprecated `.dict()` method
- **Fix**: Updated to `.model_dump()` in all adapters
- **Impact**: Compatible with Pydantic v2.x

### 3. **Automatic Timestamp Updates**
- **Issue**: `updated_at` field not automatically maintained
- **Fix**: Added `update_timestamp()` method to models, called in update operations
- **Impact**: Accurate tracking of when records were last modified

### 4. **Database Engine Caching**
- **Issue**: New database engine created on every request (performance problem)
- **Fix**: Implemented engine caching with connection pooling
- **Impact**: Better performance, proper resource management

### 5. **Email Validation**
- **Issue**: No validation of email format
- **Fix**: Added regex-based email validation in UserService and TenantAdminService
- **Impact**: Prevents invalid emails from being stored

### 6. **CRITICAL: Tenant Creation with First Admin User**
- **Issue**: SPECIFICATION.md Feature 1 requirement not implemented
- **Fix**: Created TenantAdminService with `create_tenant_with_admin()` method
- **New Endpoint**: `POST /api/v1/tenants/with-admin`
- **Impact**: Atomic tenant onboarding per specification
- **Business Rule**: First user must be an admin, both created atomically

### 7. **Improved Update Logic**
- **Issue**: Immutable fields could be accidentally modified
- **Fix**: Exclude id, tenant_id, created_at from updates
- **Impact**: Data integrity preserved

### 8. **Connection Pooling**
- **Issue**: No connection pooling for PostgreSQL
- **Fix**: Added pool_size=5, max_overflow=10, pool_pre_ping=True
- **Impact**: Better database connection management

## API Changes

### New Endpoint
```
POST /api/v1/tenants/with-admin
```
**Purpose**: Create tenant with first admin user atomically (Primary onboarding)

**Request**:
```json
{
  "tenant_name": "Lab ABC",
  "tenant_description": "ABC Laboratory",
  "admin_name": "John Doe",
  "admin_email": "john@lab-abc.com",
  "admin_password": "securepassword123"
}
```

**Response**:
```json
{
  "tenant": {
    "id": "uuid",
    "name": "Lab ABC",
    "description": "ABC Laboratory",
    "is_active": true
  },
  "admin_user": {
    "id": "uuid",
    "email": "john@lab-abc.com",
    "name": "John Doe",
    "role": "admin",
    "tenant_id": "uuid"
  }
}
```

### Modified Endpoint
```
POST /api/v1/tenants
```
**Note**: Now primarily for system admin use. Use `/with-admin` for onboarding.

## Testing Recommendations

1. **Test Composite Unique Constraint**:
   ```python
   # Should succeed
   user1 = create_user(tenant1, "test@example.com")
   user2 = create_user(tenant2, "test@example.com")  # Different tenant, OK

   # Should fail with DuplicateUserError
   user3 = create_user(tenant1, "test@example.com")  # Same tenant, FAIL
   ```

2. **Test Tenant Onboarding**:
   ```bash
   curl -X POST http://localhost:8000/api/v1/tenants/with-admin \
     -H "Content-Type: application/json" \
     -d '{
       "tenant_name": "Test Lab",
       "admin_name": "Admin User",
       "admin_email": "admin@testlab.com",
       "admin_password": "password123"
     }'
   ```

3. **Test Email Validation**:
   ```python
   # Should fail with ValueError
   create_user(tenant_id, "invalid-email", "password", "Name")
   ```

4. **Test Updated Timestamp**:
   ```python
   user = update_user(user_id, name="New Name")
   assert user.updated_at > user.created_at
   ```

## Breaking Changes

None - all changes are backward compatible or additive.

## Next Steps

1. Add integration tests for new tenant onboarding flow
2. Add unit tests for email validation
3. Test multi-tenant isolation with composite unique constraint
4. Performance test with connection pooling
