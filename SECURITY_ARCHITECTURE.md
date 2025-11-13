# Security Architecture

**Last Updated**: November 13, 2025 (v2.0.0)
**Status**: Production-ready for small user base (2-20 photographers)
**Next Review**: After adding first non-family photographer

---

## Overview

Hensler Photography uses a **two-tier architecture** with public portfolio sites (port 80/443) and authenticated management interfaces (port 443/4100). Security is based on JWT authentication, role-based access control, and data isolation by user.

**Security Model**: Defense in depth
- **Layer 1**: Firewall (port 4100 only)
- **Layer 2**: HTTPS/TLS (all traffic encrypted)
- **Layer 3**: JWT authentication (httpOnly cookies)
- **Layer 4**: Rate limiting (login endpoints)
- **Layer 5**: Database isolation (user_id filtering)

---

## Access Patterns

### Port 443 (Standard HTTPS) - Primary Access ✅

**URL Pattern**: `https://{subdomain}.hensler.photography/manage`

**Examples**:
- Admin: `https://adrian.hensler.photography/manage`
- Photographer: `https://liam.hensler.photography/manage`
- Future: `https://jane.hensler.photography/manage`

**Characteristics**:
- **Audience**: All users (admins + photographers)
- **Firewall**: Open to internet
- **Authentication**: Required (returns 401 without JWT cookie)
- **Access from**: Anywhere (home, office, mobile, coffee shop)
- **Certificate**: Standard Let's Encrypt TLS cert (no port in URL)

**Security Features**:
- ✅ JWT authentication with httpOnly cookies
- ✅ Rate limiting (5 login attempts per minute per IP)
- ✅ HTTPS with TLS 1.3
- ✅ CSRF protection (implemented via middleware)
- ✅ HSTS header (force HTTPS)
- ✅ XSS protection headers

**When to use**: Default access method for all users

---

### Port 4100 (Management) - Admin Backdoor 🔒

**URL Pattern**: `https://{subdomain}.hensler.photography:4100/manage`

**Examples**:
- Admin: `https://adrian.hensler.photography:4100/manage`
- Photographer: `https://liam.hensler.photography:4100/manage`

**Characteristics**:
- **Audience**: Admin users from trusted locations (home network)
- **Firewall**: Restricted to HOME_IP address only
- **Authentication**: Required (same JWT system as port 443)
- **Access from**: Home network only (VPN if traveling)
- **Certificate**: Let's Encrypt TLS cert (non-standard port)

**Security Features**:
- ✅ All features from port 443 (JWT, rate limiting, HTTPS)
- ✅ Additional firewall layer (only one IP allowed)
- ✅ Optional convenience for admins at home

**When to use**:
- Convenience for admin/family users at home
- Optional - port 443 is primary access method
- Not required for operation

**Important**: This is **not the only way** to access the management interface. Port 443 provides the same functionality with authentication.

---

## Multi-User Model

### User Roles

#### 1. Admin (role='admin')
**Capabilities**:
- ✅ Can manage all users (create, delete, reset passwords)
- ✅ Can view all images across all photographers
- ✅ Can access system settings and configuration
- ✅ Can view aggregated analytics across all users
- ✅ Full API access to all endpoints

**Current Users**:
- `adrian` (admin)

**Use Case**: System owner, manages platform and all photographers

---

#### 2. Photographer (role='photographer')
**Capabilities**:
- ✅ Can upload and manage own images
- ✅ Can view own analytics (impressions, clicks, views)
- ✅ Can update own profile (display name, bio)
- ✅ Can publish/unpublish own images
- ✅ Can change own password
- ❌ Cannot view other users' images
- ❌ Cannot access admin functions
- ❌ Cannot create/delete users

**Current Users**:
- `liam` (photographer)

**Use Case**: Independent photographer managing their own portfolio

---

### Data Isolation

**Database-Level Isolation**:
```python
# All image queries filtered by user_id
cursor.execute(
    "SELECT * FROM images WHERE user_id = ? AND published = 1",
    (current_user.id,)
)
```

**Protection Mechanisms**:
- ✅ **API Middleware**: `get_current_user()` dependency enforces authentication
- ✅ **Query Filtering**: All database queries include `WHERE user_id = ?`
- ✅ **File Path Validation**: Uploaded images stored with user-specific prefixes
- ✅ **Analytics Isolation**: Events linked to images via `image_id` → `user_id` chain

**Test Case**:
```bash
# Photographer liam (user_id=2) attempts to access adrian's image (user_id=1)
curl -H "Cookie: session_token=liam_jwt" \
  https://adrian.hensler.photography/api/images/123

# Result: 403 Forbidden (image belongs to different user)
```

**No Cross-User Data Leakage**:
- Image lists filtered by user_id
- Analytics show only own images
- Gallery management shows only own images
- File uploads stored in shared directory but access controlled by database

---

## Authentication Flow

### Initial Login

```
1. User visits: https://adrian.hensler.photography/manage
   ↓
2. No JWT cookie found → Redirect to /admin/login
   ↓
3. User submits login form (username + password OR Google OAuth)
   ↓
4. Backend validates credentials:
   - Password: bcrypt.verify(password, user.password_hash)
   - Google: Verify token with Google API
   ↓
5. If valid → Generate JWT token:
   - Payload: {user_id, username, role, exp: now+24h}
   - Sign with SECRET_KEY (256-bit, environment variable)
   ↓
6. Set httpOnly cookie:
   - Name: session_token
   - Value: JWT token
   - httpOnly: true (cannot be read by JavaScript)
   - Secure: true (production only, HTTPS only)
   - SameSite: Lax (CSRF protection)
   - Max-Age: 86400 (24 hours)
   ↓
7. Redirect to: /manage (photographer) or /admin (admin)
   ↓
8. All subsequent requests include cookie automatically
```

### Protected Route Access

```
1. Request to /manage/upload (protected route)
   ↓
2. Middleware: get_current_user() dependency
   ↓
3. Extract session_token from cookies
   ↓
4. Validate JWT:
   - Verify signature (SECRET_KEY)
   - Check expiration (exp claim)
   - Decode payload
   ↓
5. Load user from database by user_id
   ↓
6. If invalid/expired → 401 Unauthorized
   If valid → Continue to route handler
   ↓
7. Route handler receives current_user object
   ↓
8. Check permissions (role='admin' vs 'photographer')
   ↓
9. Return response
```

### Logout

```
1. User clicks "Logout"
   ↓
2. POST /api/auth/logout
   ↓
3. Clear session_token cookie (set max-age=0)
   ↓
4. Redirect to /admin/login
   ↓
5. JWT token still valid for up to 24h (stateless)
   BUT browser no longer sends it
```

**Note**: JWT tokens cannot be revoked server-side (stateless design). If stolen, token is valid until expiration. For higher security needs, implement refresh token pattern with server-side revocation.

---

## Threat Model

### Threats Mitigated ✅

#### 1. Brute Force Login Attacks
- **Mitigation**: Rate limiting (5 attempts per minute per IP)
- **Implementation**: `slowapi` middleware on `/api/auth/login`
- **Effect**: Attacker can only try 300 passwords per hour
- **Status**: ✅ Implemented

#### 2. Password Theft (Database Breach)
- **Mitigation**: bcrypt password hashing (cost factor 12)
- **Implementation**: `passlib[bcrypt]` with 12 rounds
- **Effect**: ~200ms per password hash (makes cracking expensive)
- **Status**: ✅ Implemented

#### 3. Session Hijacking (XSS)
- **Mitigation**: httpOnly cookies (JavaScript cannot read)
- **Implementation**: `response.set_cookie(httponly=True)`
- **Effect**: XSS cannot steal JWT token
- **Status**: ✅ Implemented

#### 4. Man-in-the-Middle Attacks
- **Mitigation**: HTTPS with TLS 1.3
- **Implementation**: Let's Encrypt certificates via Caddy
- **Effect**: All traffic encrypted
- **Status**: ✅ Implemented

#### 5. SQL Injection
- **Mitigation**: Parameterized queries (no string concatenation)
- **Implementation**: `cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))`
- **Effect**: User input never executed as SQL
- **Status**: ✅ Implemented

#### 6. Cross-User Data Access
- **Mitigation**: Database-level filtering by user_id
- **Implementation**: All queries include `WHERE user_id = ?`
- **Effect**: Users cannot see others' images/data
- **Status**: ✅ Implemented

#### 7. Clickjacking
- **Mitigation**: X-Frame-Options: DENY header
- **Implementation**: Caddy configuration
- **Effect**: Cannot embed in iframe
- **Status**: ✅ Implemented

#### 8. MIME Type Confusion
- **Mitigation**: X-Content-Type-Options: nosniff
- **Implementation**: Caddy configuration
- **Effect**: Browser respects Content-Type header
- **Status**: ✅ Implemented

---

### Threats Partially Mitigated ⚠️

#### 1. CSRF (Cross-Site Request Forgery)
- **Status**: ⚠️ Partially mitigated
- **Current Protection**:
  - SameSite=Lax cookies (blocks most CSRF)
  - CORS configuration (restricts origins)
- **Remaining Risk**:
  - Sophisticated CSRF attacks still possible
  - GET requests can be exploited
- **Recommended**: Implement CSRF tokens for state-changing operations
- **Priority**: MEDIUM (SameSite provides good baseline)

#### 2. Session Revocation
- **Status**: ⚠️ Cannot revoke sessions
- **Current Implementation**: Stateless JWT (24hr validity)
- **Remaining Risk**:
  - Stolen token valid until expiration
  - Password change doesn't invalidate existing sessions
  - No "log out all devices" functionality
- **Recommended**: Implement refresh token pattern with server-side storage
- **Priority**: MEDIUM (24hr expiration limits exposure)

#### 3. Account Enumeration
- **Status**: ⚠️ Partially protected
- **Current Protection**: Same error message for invalid username/password
- **Remaining Risk**: Timing attacks may reveal valid usernames
- **Recommended**: Add random delay to failed logins
- **Priority**: LOW (small user base, low risk)

---

### Threats Not Mitigated 🔴

#### 1. Forgotten Password Recovery
- **Status**: 🔴 No mechanism
- **Current State**: User locked out if password forgotten
- **Workaround**: Admin can reset password via CLI: `python -m api.cli set-password username`
- **Impact**: HIGH for photographers, LOW for family users
- **Recommended**: Implement email-based password reset flow
- **Priority**: HIGH (before adding non-family users)

#### 2. Two-Factor Authentication (2FA)
- **Status**: 🔴 Not implemented
- **Current State**: Password-only authentication
- **Risk**: Email compromise = account takeover
- **Recommended**: Add TOTP-based 2FA (Google Authenticator)
- **Priority**: MEDIUM (not critical for family users)

#### 3. Account Takeover via Email Compromise
- **Status**: 🔴 No protection
- **Current State**: If attacker compromises email, can use password reset (when implemented)
- **Mitigation**: 2FA required
- **Priority**: MEDIUM (depends on password reset implementation)

#### 4. DDoS (Distributed Denial of Service)
- **Status**: 🔴 No network-layer protection
- **Current Protection**: API-level rate limiting only
- **Risk**: Attacker can overwhelm VPS with requests
- **Recommended**: Cloudflare proxy (when traffic justifies)
- **Priority**: LOW (small user base, low risk)

#### 5. Malicious File Uploads
- **Status**: ⚠️ Partial protection
- **Current Protection**:
  - File size limits (20MB)
  - File type checking (JPEG/PNG/GIF/WebP)
- **Remaining Risk**:
  - Malicious EXIF data
  - Polyglot files (valid image + malicious script)
  - Path traversal in filenames (partially mitigated)
- **Recommended**:
  - Strip EXIF before storing (preserve in database only)
  - Re-encode images (removes embedded scripts)
  - Sandbox image processing
- **Priority**: MEDIUM (affects all upload features)

#### 6. API Abuse / Scraping
- **Status**: 🔴 No protection
- **Current State**: Authenticated users can query API unlimited times
- **Risk**: User could scrape all data via API
- **Recommended**: Per-user rate limiting (beyond just login)
- **Priority**: LOW (trust-based model for now)

---

## Authentication Implementation Details

### JWT Token Structure

**Claims**:
```json
{
  "user_id": 1,
  "username": "adrian",
  "role": "admin",
  "exp": 1699900000,
  "iat": 1699813600
}
```

**Signature**:
- Algorithm: HS256 (HMAC-SHA256)
- Secret: 256-bit random key (environment variable: `JWT_SECRET_KEY`)
- Validation: Signature verified on every request

**Expiration**:
- Access token: 24 hours
- No refresh token (future enhancement)

### Password Storage

**Hashing**:
- Algorithm: bcrypt
- Cost factor: 12 rounds (~200ms per hash)
- Salt: Automatic (embedded in bcrypt hash)

**Example Hash**:
```
$2b$12$XkwLN.qLqcN/5VdY8xZ1eeF7OqT4Yh3PqT0YqH3OqT4Yh3PqT0Yq
   ^   ^  ^-- Salt (22 chars) + Hash (31 chars)
   |   |
   |   Cost factor (12 = 2^12 = 4096 iterations)
   Algorithm (2b = bcrypt)
```

**Password Validation**:
```python
# During login
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
is_valid = pwd_context.verify(plain_password, user.password_hash)
```

### Password Requirements

**Current Rules** (enforced in Pydantic model):
- Minimum length: 12 characters
- Must contain: uppercase, lowercase, number
- No common password check (future enhancement)

**Validation**:
```python
class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, regex="^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)")
```

### Cookie Configuration

**Production** (`secure=True`):
```python
response.set_cookie(
    key="session_token",
    value=jwt_token,
    httponly=True,        # Cannot be read by JavaScript
    secure=True,          # HTTPS only
    samesite="lax",       # CSRF protection
    max_age=86400,        # 24 hours
    path="/",             # All paths
    domain=None           # Current domain only
)
```

**Development** (`secure=False`):
- Same as production except `secure=False` (allows HTTP)
- Detected via `os.getenv("ENVIRONMENT") == "production"`

---

## Scaling Considerations

### Current Capacity (v2.0.0)

**Infrastructure**:
- VPS: 2-4 CPU cores, 4-8GB RAM
- Database: SQLite (~100k images capacity)
- Storage: Local filesystem (~500GB)
- Concurrent Users: ~10-20 comfortable

**Bottlenecks**:
1. **SQLite Write Concurrency**: ~10 concurrent writes max
2. **Image Processing**: CPU-bound (WebP generation)
3. **Storage**: Single disk I/O
4. **TLS Certificates**: 50 certs per domain per week (Let's Encrypt limit)

**Sufficient For**:
- ✅ 2-20 photographers
- ✅ <100k total images
- ✅ <10 concurrent uploads
- ✅ <100 requests per second

---

### Adding New Photographers

**Process** (admin-initiated):

```bash
# 1. Create user in database
cd /opt/prod/hensler_photography
docker compose exec api python -m api.cli create-user jane jane@example.com photographer

# 2. Set initial password
docker compose exec api python -m api.cli set-password jane

# 3. Configure subdomain (DNS)
# Add A record: jane.hensler.photography → VPS_IP

# 4. Send credentials to photographer
# Via secure channel (Signal, 1Password share, etc.)

# 5. Photographer logs in
# URL: https://jane.hensler.photography/manage
# First action: Change password in settings

# 6. Let's Encrypt automatically issues TLS cert
# No manual intervention needed
```

**Subdomain Assignment**:
- Pattern: `{username}.hensler.photography`
- DNS: All subdomains point to same VPS IP
- Caddy: Routes based on subdomain Host header
- Database: `users.subdomain` field (currently nullable)

**User Limit** (Let's Encrypt):
- 50 certificates per week per domain
- Can add 50 new photographers per week
- Not a practical limitation for this use case

---

### When to Migrate

#### PostgreSQL Migration
**When**:
- More than 10 active photographers
- More than 50,000 images
- Need concurrent write performance
- Need full-text search

**Benefits**:
- Better write concurrency
- Connection pooling
- Advanced querying (full-text, JSON)
- Replication and backups

**Migration Path**:
- Use Alembic for schema migrations
- Export SQLite → Import PostgreSQL
- Update `DATABASE_PATH` to PostgreSQL connection string
- Minimal code changes (same aiosqlite-like API)

---

#### CDN Integration
**When**:
- Bandwidth exceeds 500GB/month
- Users complain about slow image loading
- Want global distribution

**Benefits**:
- Faster image delivery worldwide
- Reduced VPS bandwidth costs
- DDoS protection (if using Cloudflare)
- Cache invalidation on image update

**Options**:
- Cloudflare (free tier available)
- AWS CloudFront
- Bunny CDN (photography-optimized)

---

#### Redis Session Store
**When**:
- Need to revoke sessions immediately
- Implement refresh token pattern
- Want "log out all devices" feature

**Benefits**:
- Server-side session revocation
- Shorter access token expiration (5-15 min)
- Better security (stolen token revocable)

**Implementation**:
- Store refresh tokens in Redis
- Access tokens still JWT (5 min expiration)
- Refresh endpoint exchanges tokens

---

#### Load Balancer
**When**:
- More than 50 concurrent users
- API response times degrade
- Single VPS cannot handle traffic

**Benefits**:
- Horizontal scaling (multiple API containers)
- Zero-downtime deployments
- Health checks and failover

**Options**:
- Nginx or HAProxy (self-hosted)
- Cloud load balancers (AWS ALB, GCP)

---

## Security Checklist (Before Going Public)

### Critical (Must Complete) 🔴

- [ ] **Password Reset Flow**: Implement email-based password recovery
- [ ] **User Settings Page**: UI for password change, profile editing
- [ ] **CSRF Tokens**: Implement for all state-changing operations
- [ ] **Audit Foreign Keys**: Verify `PRAGMA foreign_keys = ON` in database
- [ ] **Test User Isolation**: Verify photographer cannot access admin/other users' data
- [ ] **Review Audit Logging**: Ensure all destructive actions are logged

### High Priority (Strongly Recommended) 🟡

- [ ] **Refresh Token Pattern**: Implement for session revocation capability
- [ ] **File Upload Security**: Strip EXIF, re-encode images, sandbox processing
- [ ] **Per-User Rate Limiting**: Prevent API abuse beyond login
- [ ] **Email Verification**: Verify email ownership on account creation
- [ ] **Backup System**: Implement automated daily backups (see BACKUP.md)

### Medium Priority (Nice to Have) 🟢

- [ ] **Two-Factor Authentication**: TOTP-based 2FA (Google Authenticator)
- [ ] **Password Strength Meter**: Visual feedback on password security
- [ ] **Common Password Check**: Block passwords from breach databases
- [ ] **Session Management UI**: Show active sessions, revoke individual sessions
- [ ] **Security Headers**: CSP (Content Security Policy) headers

### Low Priority (Future Enhancement) ⚪

- [ ] **Account Activity Log**: Show user login history, IP addresses
- [ ] **OAuth Multiple Providers**: Add GitHub, Microsoft
- [ ] **API Key Authentication**: For programmatic access
- [ ] **Webhooks**: Notify external services of image uploads
- [ ] **Read-Only Public API**: Allow embedding galleries on external sites

---

## Security Contacts

**Security Issues**: Report to adrian@hensler.photography
**Response Time**: 24 hours for critical issues
**Disclosure Policy**: Coordinated disclosure (30 day embargo)

---

## Version History

- **v2.0.0** (Nov 13, 2025): Initial security architecture documentation
  - JWT authentication implemented
  - Rate limiting active
  - Multi-user model with role-based access
  - Port 443 primary access, port 4100 admin backdoor

**Next Review**: After adding first non-family photographer
