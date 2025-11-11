# Hensler Photography - Task List

**Last Updated**: 2025-11-02
**Current Sprint**: Sprint 4 (Multi-User Reorganization)
**Status**: Planning Complete, Ready for Implementation

---

## Current Sprint: Sprint 4 - Multi-User Reorganization

**Goal**: Implement authentication, move admin to main domain, create photographer dashboards.

**Timeline**: 2-3 weeks (~18-22 hours)
**Start Date**: After Sprint 3 sign-off
**Target Completion**: TBD

---

### Phase 1: Documentation ✅ **COMPLETE**

**Goal**: Document current architecture and future roadmap

**Tasks**:
- [x] Create ARCHITECTURE.md (comprehensive system documentation)
- [x] Create ROADMAP.md (sprint timeline and chatbot design)
- [x] Create TODO.md (this file - Sprint 4 checklist)
- [ ] Commit all documentation to GitHub

**Duration**: 2-3 hours
**Status**: ✅ Complete (pending commit)

---

### Phase 2: Move Admin Interface to Main Domain

**Goal**: Migrate admin from `adrian.hensler.photography:4100` to `hensler.photography/admin`

#### 2.1 Update Caddyfile Configuration

- [ ] **Update `Caddyfile.local`** (development):
  - [ ] Add `/admin*` handler to `hensler.photography:8080` block
  - [ ] Add `/api/*` handler to `hensler.photography:8080` block
  - [ ] Add `/assets/gallery/*` handler to `hensler.photography:8080` block
  - [ ] Remove entire `adrian.hensler.photography:4100` block
  - [ ] Test with `caddy fmt` to validate syntax

- [ ] **Update `Caddyfile`** (production):
  - [ ] Mirror changes from Caddyfile.local (same handlers, no port numbers)
  - [ ] Validate syntax with `caddy fmt`

**Example Caddyfile.local structure**:
```caddy
hensler.photography:8080 {
    handle /admin* {
        reverse_proxy api:8000
    }
    handle /api/* {
        reverse_proxy api:8000
    }
    handle /assets/gallery/* {
        reverse_proxy api:8000
    }
    handle {
        root * /srv/sites/main
        file_server
        encode zstd gzip
    }
}
```

#### 2.2 Update Docker Compose Configuration

- [ ] **Update `docker-compose.local.yml`**:
  - [ ] Remove port `4100:4100` mapping from web service
  - [ ] Verify `8080:8080` is the only public port
  - [ ] Add environment variable: `JWT_SECRET_KEY=${JWT_SECRET_KEY}`

- [ ] **Update `docker-compose.yml`** (production):
  - [ ] Mirror changes from docker-compose.local.yml
  - [ ] Ensure no port 4100 references

#### 2.3 Update CORS Configuration

- [ ] **Edit `api/main.py`**:
  - [ ] Add `https://hensler.photography` to allowed origins
  - [ ] Add `https://hensler.photography:8080` (dev) to allowed origins
  - [ ] Remove `https://adrian.hensler.photography:4100` (deprecated)

**Updated CORS**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://hensler.photography",
        "https://adrian.hensler.photography",
        "https://liam.hensler.photography",
        "https://hensler.photography:8080",
        "https://adrian.hensler.photography:8080",
        "https://liam.hensler.photography:8080",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### 2.4 Testing

- [ ] Start dev containers: `docker compose -p hensler_test -f docker-compose.local.yml up -d`
- [ ] Test admin dashboard: `curl http://localhost:8080/admin` (should redirect to login after auth implemented)
- [ ] Test API health: `curl http://localhost:8080/api/health`
- [ ] Verify port 4100 is NOT exposed: `docker ps` (should show only 8080)
- [ ] Test in browser: `http://localhost:8080/admin`
- [ ] Check for CORS errors in browser console

#### 2.5 Deployment

- [ ] Commit changes to git: "Move admin interface to main domain (Sprint 4 Phase 2)"
- [ ] Push to feature branch: `git push origin feature/backend-api`
- [ ] Deploy to production: `cd /opt/prod && git pull && docker compose restart`
- [ ] Verify production: `curl -I https://hensler.photography/admin`

**Duration**: 3 hours
**Dependencies**: None
**Status**: ⏳ Not Started

---

### Phase 3: Implement Authentication System

**Goal**: Add JWT-based authentication with httpOnly cookies

#### 3.1 Database Migration

- [ ] **Add password_hash column to users table**:
  - [ ] Create migration script: `api/migrations/001_add_password_hash.py`
  - [ ] SQL: `ALTER TABLE users ADD COLUMN password_hash TEXT;`
  - [ ] Run migration on dev database
  - [ ] Verify column exists: `sqlite3 api/hensler_photography.db ".schema users"`

- [ ] **Seed passwords for Adrian and Liam**:
  - [ ] Generate bcrypt hashes for initial passwords (cost factor 12)
  - [ ] Update users table: `UPDATE users SET password_hash = ? WHERE id = 1;`
  - [ ] Update users table: `UPDATE users SET password_hash = ? WHERE id = 2;`
  - [ ] Document initial passwords in secure location (not git)

**Migration script example**:
```python
import sqlite3
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Add column
conn = sqlite3.connect("api/hensler_photography.db")
cursor = conn.cursor()
cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT;")

# Seed passwords (use strong passwords in production!)
adrian_hash = pwd_context.hash("CHANGE_ME_ADRIAN")
liam_hash = pwd_context.hash("CHANGE_ME_LIAM")

cursor.execute("UPDATE users SET password_hash = ? WHERE id = 1", (adrian_hash,))
cursor.execute("UPDATE users SET password_hash = ? WHERE id = 2", (liam_hash,))

conn.commit()
conn.close()
```

#### 3.2 Install Authentication Dependencies

- [ ] **Update `api/requirements.txt`**:
  - [ ] Add `passlib[bcrypt]==1.7.4` (password hashing)
  - [ ] Add `python-jose[cryptography]==3.3.0` (JWT tokens)
  - [ ] Add `python-multipart==0.0.6` (form data parsing)

- [ ] **Rebuild Docker image**:
  - [ ] `docker compose -p hensler_test -f docker-compose.local.yml build api`
  - [ ] Verify dependencies installed: `docker compose exec api pip list | grep passlib`

#### 3.3 Create Authentication Routes

- [ ] **Create `api/routes/auth.py`**:
  - [ ] Implement `POST /api/auth/login` (username, password → JWT cookie)
  - [ ] Implement `POST /api/auth/logout` (clear session cookie)
  - [ ] Implement `GET /api/auth/me` (return current user info)
  - [ ] Implement `POST /api/auth/register` (admin only, create new user)
  - [ ] Implement `POST /api/auth/change-password` (update password)

**Login endpoint structure**:
```python
@router.post("/api/auth/login")
async def login(
    username: str = Form(...),
    password: str = Form(...),
    response: Response
):
    # 1. Get user from database
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(401, "Invalid credentials")

    # 2. Verify password
    if not pwd_context.verify(password, user.password_hash):
        raise HTTPException(401, "Invalid credentials")

    # 3. Generate JWT token
    token = jwt.encode(
        {
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "exp": datetime.utcnow() + timedelta(hours=24)
        },
        SECRET_KEY,
        algorithm="HS256"
    )

    # 4. Set httpOnly cookie
    response.set_cookie(
        key="session_token",
        value=token,
        httponly=True,
        secure=is_production(),
        samesite="lax",
        max_age=86400  # 24 hours
    )

    return {"success": True, "user": {"id": user.id, "username": user.username, "role": user.role}}
```

#### 3.4 Create Authentication Middleware

- [ ] **Implement `get_current_user()` dependency in `api/routes/auth.py`**:
  - [ ] Read `session_token` cookie from request
  - [ ] Validate JWT signature and expiration
  - [ ] Load user from database by user_id
  - [ ] Return User object or raise HTTPException(401)

**get_current_user example**:
```python
async def get_current_user(request: Request) -> User:
    """Dependency that validates JWT and returns current user"""
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(401, "Not authenticated")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = get_user_by_id(payload["user_id"])
        if not user:
            raise HTTPException(401, "User not found")
        return user
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")
```

#### 3.5 Build Login Page

- [ ] **Create `api/templates/admin/login.html`**:
  - [ ] Username input field
  - [ ] Password input field
  - [ ] "Login" button
  - [ ] Error message display area
  - [ ] POST form to `/api/auth/login`
  - [ ] Redirect to `/admin` on success
  - [ ] Style with Apple-inspired design

**Login page structure**:
```html
<!DOCTYPE html>
<html>
<head>
    <title>Login - Hensler Photography Admin</title>
    <style>
        /* Apple-inspired minimal design */
    </style>
</head>
<body>
    <div class="login-container">
        <h1>Hensler Photography</h1>
        <form id="login-form">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Log In</button>
            <div id="error-message" style="display: none;"></div>
        </form>
    </div>

    <script>
        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });

            if (response.ok) {
                window.location.href = '/admin';
            } else {
                const error = await response.json();
                document.getElementById('error-message').textContent = error.detail;
                document.getElementById('error-message').style.display = 'block';
            }
        });
    </script>
</body>
</html>
```

#### 3.6 Protect Admin Routes

- [ ] **Update `api/main.py` admin routes**:
  - [ ] Add `current_user: User = Depends(get_current_user)` to `/admin` route
  - [ ] Add `current_user: User = Depends(get_current_user)` to `/admin/upload` route
  - [ ] Add `current_user: User = Depends(get_current_user)` to `/admin/gallery` route
  - [ ] Add admin role check: `if current_user.role != 'admin': raise HTTPException(403)`
  - [ ] Add redirect to login if not authenticated

**Protected route example**:
```python
@app.get("/admin")
async def admin_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    # Check admin role
    if current_user.role != 'admin':
        raise HTTPException(403, "Admin access required")

    # Load all images (admin sees everything)
    images = get_all_images()

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "current_user": current_user,
        "images": images
    })
```

#### 3.7 Add Logout Functionality

- [ ] **Update admin dashboard template (`api/templates/admin/dashboard.html`)**:
  - [ ] Add "Logout" button in header
  - [ ] POST to `/api/auth/logout` on click
  - [ ] Redirect to `/admin/login` after logout

**Logout button**:
```html
<div class="header">
    <h1>Hensler Photography Admin</h1>
    <div class="user-menu">
        <span>Welcome, {{ current_user.display_name }}</span>
        <button onclick="logout()">Logout</button>
    </div>
</div>

<script>
    async function logout() {
        await fetch('/api/auth/logout', {method: 'POST', credentials: 'include'});
        window.location.href = '/admin/login';
    }
</script>
```

#### 3.8 Testing Authentication

- [ ] Test login with correct credentials (Adrian, Liam)
- [ ] Test login with incorrect password (should fail)
- [ ] Test login with non-existent user (should fail)
- [ ] Test accessing `/admin` without login (should redirect to `/admin/login`)
- [ ] Test accessing `/admin` with valid session (should succeed)
- [ ] Test logout (should clear cookie and redirect)
- [ ] Test session expiry (wait 24 hours or manually expire token)
- [ ] Test HTTPS cookie security in production

**Duration**: 8-10 hours
**Dependencies**: Phase 2 complete
**Status**: ⏳ Not Started

---

### Phase 4: Photographer Dashboards

**Goal**: Create `/manage` interfaces for photographers on their subdomains

#### 4.1 Create Photographer Templates

- [ ] **Create directory**: `api/templates/photographer/`

- [ ] **Create `api/templates/photographer/dashboard.html`**:
  - [ ] Show only current user's images (filtered by user_id)
  - [ ] Display statistics (total images, published, unpublished)
  - [ ] Quick actions (Upload, View Gallery)
  - [ ] Recent uploads list
  - [ ] Logout button

- [ ] **Create `api/templates/photographer/upload.html`**:
  - [ ] Same as admin upload but user_id is fixed to current_user.id
  - [ ] Cannot select user (dropdown hidden)

- [ ] **Create `api/templates/photographer/gallery.html`**:
  - [ ] Same as admin gallery but filtered to current_user.id
  - [ ] Cannot see other photographers' images
  - [ ] Can only edit/delete own images

#### 4.2 Add /manage Routes

- [ ] **Create `/manage` routes in `api/main.py`**:
  - [ ] `GET /manage` → Photographer dashboard
  - [ ] `GET /manage/upload` → Upload interface
  - [ ] `GET /manage/gallery` → Gallery management
  - [ ] All routes require authentication: `current_user = Depends(get_current_user)`
  - [ ] All routes filter by `current_user.id`

**Photographer dashboard route**:
```python
@app.get("/manage")
async def photographer_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    # Get current user's images only
    images = get_images_by_user(current_user.id)

    stats = {
        "total": len(images),
        "published": sum(1 for img in images if img.published),
        "unpublished": sum(1 for img in images if not img.published)
    }

    return templates.TemplateResponse("photographer/dashboard.html", {
        "request": request,
        "current_user": current_user,
        "images": images,
        "stats": stats
    })
```

#### 4.3 Update Caddyfile for /manage Routes

- [ ] **Add `/manage*` handlers to subdomain blocks in `Caddyfile.local`**:
  - [ ] `liam.hensler.photography:8080` → `/manage*` → reverse_proxy api:8000
  - [ ] `adrian.hensler.photography:8080` → `/manage*` → reverse_proxy api:8000

**Example**:
```caddy
liam.hensler.photography:8080 {
    handle /manage* {
        reverse_proxy api:8000  # Photographer dashboard
    }
    handle /assets/gallery/* {
        reverse_proxy api:8000
    }
    handle {
        root * /srv/sites/liam
        file_server
        encode zstd gzip
    }
}
```

- [ ] **Mirror changes in `Caddyfile`** (production)

#### 4.4 Implement User Isolation in API

- [ ] **Update `api/routes/ingestion.py` endpoints**:
  - [ ] `GET /api/images/list` - Filter by current_user.id if not admin
  - [ ] `PATCH /api/images/{id}` - Verify ownership if not admin
  - [ ] `DELETE /api/images/{id}` - Verify ownership if not admin
  - [ ] `POST /api/images/ingest` - Set user_id to current_user.id if not admin

**User isolation example**:
```python
@router.get("/api/images/list")
async def list_images(
    current_user: User = Depends(get_current_user),
    user_id: int = None,  # Admin can specify, others ignored
    published: bool = None
):
    # If not admin, force filter to current user
    if current_user.role != 'admin':
        user_id = current_user.id

    # Build query
    query = "SELECT * FROM images WHERE 1=1"
    params = []

    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)

    if published is not None:
        query += " AND published = ?"
        params.append(published)

    return execute_query(query, params)
```

#### 4.5 Frontend Permission-Based UI

- [ ] **Update admin templates to show/hide based on role**:
  - [ ] Hide "All Photographers" dropdown if not admin
  - [ ] Show "Admin Dashboard" link only to admin
  - [ ] Show "My Dashboard" link to all users
  - [ ] Display current user's role in header

**Permission check in template**:
```html
{% if current_user.role == 'admin' %}
    <a href="/admin" class="nav-link">Admin Dashboard</a>
{% endif %}

<a href="/manage" class="nav-link">My Dashboard</a>
```

#### 4.6 Testing Photographer Dashboards

- [ ] Test as Adrian (admin):
  - [ ] Can access `/admin` ✓
  - [ ] Can access `/manage` ✓
  - [ ] Can see all images in admin gallery ✓
  - [ ] Can see only own images in /manage ✓
- [ ] Test as Liam (photographer):
  - [ ] Cannot access `/admin` ✗ (403 error)
  - [ ] Can access `/manage` ✓
  - [ ] Can only see own images ✓
  - [ ] Cannot edit Adrian's images ✗
  - [ ] Cannot delete Adrian's images ✗
- [ ] Test unauthenticated:
  - [ ] Cannot access `/admin` ✗ (redirect to login)
  - [ ] Cannot access `/manage` ✗ (redirect to login)

**Duration**: 5-6 hours
**Dependencies**: Phase 3 complete
**Status**: ⏳ Not Started

---

### Phase 5: Final Testing & Deployment

#### 5.1 Comprehensive Testing

- [ ] **Security Testing**:
  - [ ] Attempt SQL injection on login form
  - [ ] Attempt XSS in username field
  - [ ] Attempt CSRF attack on state-changing endpoints
  - [ ] Verify httpOnly cookies cannot be accessed from JavaScript
  - [ ] Verify session expires after 24 hours
  - [ ] Verify Secure flag is set in production (HTTPS-only)

- [ ] **User Isolation Testing**:
  - [ ] Log in as Liam, attempt to access Adrian's image via API
  - [ ] Log in as Liam, attempt to edit Adrian's image via API
  - [ ] Log in as Liam, attempt to delete Adrian's image via API
  - [ ] Verify database queries include user_id filter for non-admin

- [ ] **Workflow Testing**:
  - [ ] Adrian logs in, uploads image for Liam
  - [ ] Liam logs in, sees new image in /manage
  - [ ] Liam edits metadata, publishes image
  - [ ] Verify image appears on liam.hensler.photography public site
  - [ ] Adrian logs in to /admin, sees Liam's published image

- [ ] **Browser Testing**:
  - [ ] Chrome (desktop and mobile)
  - [ ] Firefox (desktop and mobile)
  - [ ] Safari (desktop and mobile)
  - [ ] Edge (desktop)

#### 5.2 Performance Testing

- [ ] Measure login response time (<200ms target)
- [ ] Measure authenticated page load time (<500ms target)
- [ ] Measure API endpoint latency with authentication overhead
- [ ] Check database query performance (add indexes if needed)

#### 5.3 Documentation Updates

- [ ] Update ARCHITECTURE.md with actual implementation details
- [ ] Update ROADMAP.md with Sprint 4 completion date
- [ ] Update CHANGELOG.md with Sprint 4 release notes
- [ ] Update CLAUDE.md with authentication workflow
- [ ] Update sites/adrian/README.md with /manage instructions

#### 5.4 Production Deployment

- [ ] **Pre-deployment Checklist**:
  - [ ] All tests passing ✓
  - [ ] Documentation updated ✓
  - [ ] Environment variables set in production (JWT_SECRET_KEY) ✓
  - [ ] Database migration tested on production backup ✓
  - [ ] Rollback plan documented ✓

- [ ] **Deployment Steps**:
  - [ ] Commit all changes: "Complete Sprint 4 - Multi-User Reorganization"
  - [ ] Push to feature branch: `git push origin feature/backend-api`
  - [ ] Merge to main branch (after review)
  - [ ] SSH to production VPS
  - [ ] Backup database: `cp api/hensler_photography.db api/hensler_photography.db.backup.sprint4`
  - [ ] Pull changes: `cd /opt/prod/hensler_photography && git pull origin main`
  - [ ] Run database migration: `python api/migrations/001_add_password_hash.py`
  - [ ] Rebuild containers: `docker compose build`
  - [ ] Restart services: `docker compose restart`
  - [ ] Verify production health: `curl https://hensler.photography/api/health`

- [ ] **Post-deployment Verification**:
  - [ ] Test login at `https://hensler.photography/admin/login`
  - [ ] Verify SSL certificates valid (green padlock)
  - [ ] Test as Adrian (admin role)
  - [ ] Test as Liam (photographer role)
  - [ ] Verify public sites still accessible (no auth required)
  - [ ] Check logs for errors: `docker compose logs api`
  - [ ] Monitor for 24 hours for issues

#### 5.5 User Communication

- [ ] **Notify Adrian** (project owner):
  - [ ] Sprint 4 complete, authentication enabled
  - [ ] New login URL: `https://hensler.photography/admin`
  - [ ] Provide initial password (change immediately)
  - [ ] Walkthrough of new features

- [ ] **Notify Liam** (photographer):
  - [ ] Personal dashboard available at `https://liam.hensler.photography/manage`
  - [ ] Provide initial password (change immediately)
  - [ ] Explain how to upload, edit, publish images
  - [ ] Show how to use AI-powered metadata

**Duration**: 3-4 hours
**Dependencies**: Phase 4 complete
**Status**: ⏳ Not Started

---

## Sprint 5 Planning: AI Chatbot Assistant (Future)

**Status**: 📋 Documented, implementation on hold until Sprint 4 complete

**High-Level Tasks** (to be expanded later):
- [ ] Create conversations and messages tables
- [ ] Implement streaming endpoint: `POST /api/chat/message`
- [ ] Build tool functions (list_images, get_details, suggest_tags, update_metadata, publish, find_similar)
- [ ] Implement user isolation in tool functions
- [ ] Add confirmation flow for state-changing actions
- [ ] Implement rate limiting (20 messages/hour)
- [ ] Build chat widget UI in `/manage` dashboard
- [ ] Test with various prompts and edge cases
- [ ] Document chatbot capabilities in user guide

**See ROADMAP.md for detailed chatbot design and architecture.**

---

## Backlog: Future Sprints

### Sprint 6: Analytics Dashboard
- [ ] Add tracking script to public sites
- [ ] Create image_events table
- [ ] Build analytics dashboard at `/manage/analytics`
- [ ] Implement popular images report
- [ ] Add CSV export functionality

### Sprint 7: Static Site Generator
- [ ] Build photo detail page template
- [ ] Implement `/photo/{slug}` routes
- [ ] Add Open Graph meta tags
- [ ] Generate sitemap.xml
- [ ] Implement pagination

### Sprint 8+: E-Commerce, Advanced Search, etc.
- See ROADMAP.md for full list of future enhancements

---

## Bug Fixes & Technical Debt

**Known Issues** (to be addressed organically during use):
- [ ] Review error handling edge cases as they're discovered
- [ ] Test with various image formats (HEIC, RAW, etc.)
- [ ] Optimize Claude Vision prompt based on analysis quality
- [ ] Add retry logic for transient API failures
- [ ] Improve WebP generation quality settings

**Technical Debt**:
- [ ] Add database connection pooling (if performance issues arise)
- [ ] Implement API endpoint rate limiting (Sprint 5)
- [ ] Add CSRF protection (Sprint 4)
- [ ] Migrate to PostgreSQL (if scaling beyond single server)
- [ ] Add CDN for image delivery (future)

**UI/UX Improvements**:
- [ ] Remove "Upload" link from upload page navigation (redundant - already on the page)

---

## Notes & Decisions

### Sprint 4 Decisions (User Approved)
- ✅ Dashboard URL: `/manage` (chosen over `/dashboard`, `/photographer`, `/gallery`)
- ✅ User creation: Admin-only, prepopulate Adrian (admin) and Liam (photographer)
- ✅ Chatbot: Hold for Sprint 5, document and plan now
- ✅ Timeline: Start Sprint 4 after Sprint 3 complete

### Environment Variables Needed
- `JWT_SECRET_KEY` - Secret for signing JWT tokens (generate with `openssl rand -hex 32`)
- `ANTHROPIC_API_KEY` - Already set, used for Claude Vision
- `DATABASE_PATH` - Path to SQLite database (default: `/app/hensler_photography.db`)

### Security Considerations
- **Password Storage**: Never commit plaintext passwords to git
- **JWT Secret**: Generate strong secret, store in `.env` file (not in git)
- **Initial Passwords**: Require users to change password on first login
- **Session Duration**: 24 hours (configurable in auth.py)
- **Cookie Security**: httpOnly=True, Secure=True (prod), SameSite=Lax

---

## Progress Tracking

### Sprint 4 Progress
- [ ] Phase 1: Documentation - ✅ **COMPLETE** (2.5 hours)
- [ ] Phase 2: Move Admin to Main Domain - ⏳ Not Started (est. 3 hours)
- [ ] Phase 3: Authentication System - ⏳ Not Started (est. 8-10 hours)
- [ ] Phase 4: Photographer Dashboards - ⏳ Not Started (est. 5-6 hours)
- [ ] Phase 5: Testing & Deployment - ⏳ Not Started (est. 3-4 hours)

**Total Estimated**: 18-22 hours
**Completed**: 2.5 hours (11-14%)
**Remaining**: 15.5-19.5 hours

---

**Last Updated**: 2025-11-11
**Maintained By**: Adrian Hensler
**Next Review**: After Sprint 4 Phase 2 complete

---

## Future Enhancements - Gallery Optimization & Image Protection

### Phase 2: Public Gallery Optimization (WebP Variants)

**Status**: Not Started
**Priority**: Medium
**Estimated Effort**: 4-6 hours
**Added**: 2025-11-11

#### Description
Public gallery currently serves full-resolution original images. System already generates WebP variants (400px, 800px, 1200px) during upload, but they're not being used by the public gallery.

#### Benefits
- **10-20x faster page loads**, especially on mobile
- Lower bandwidth costs
- Better SEO (improved Core Web Vitals)
- Enable progressive enhancement (blur-up placeholders)

#### Implementation Tasks
1. Update `/api/gallery/published` to return variant URLs
2. Modify frontend JavaScript to load appropriate sizes:
   - 400px thumbnails for grid view
   - 1200px WebP for lightbox
   - Optional full-res on-demand
3. Implement responsive loading with `<picture>` or `srcset`
4. Add lazy loading for off-screen images
5. Test across devices and network speeds

#### Technical Notes
- WebP variants already exist in `image_variants` table
- Infrastructure complete, just needs API + frontend wiring
- Consider adding blur-up placeholder technique

---

### Gallery Size Control & Image Protection

**Status**: Not Started
**Priority**: Medium
**Estimated Effort**: 3-4 hours
**Added**: 2025-11-11

#### Description
Allow photographers to control whether visitors can view/download full-resolution images. Gives photographers flexibility between showcasing work at highest quality vs. protecting against unauthorized use.

#### Features

**Per-Photographer Settings** (portfolio-wide defaults):
- `allow_full_size_viewing`: Show full-res in lightbox vs. 1200px max
- `allow_downloads`: Enable/disable download button
- `watermark_images` (future): Apply watermark to downloads

**Per-Image Override**:
- Optional fields in `images` table to override portfolio defaults

**Gallery UI**:
- Add "View Settings" section to `/manage` dashboard
- Toggle switches for settings
- Override options in image edit modal
- Display "Protected" badge on gallery management

**Public Gallery Enforcement**:
- `/api/gallery/published` respects `allow_full_size_viewing`
- Frontend lightbox checks `allow_downloads` flag

#### Database Migration
```sql
ALTER TABLE users ADD COLUMN allow_full_size_viewing INTEGER DEFAULT 1;
ALTER TABLE users ADD COLUMN allow_downloads INTEGER DEFAULT 1;
ALTER TABLE images ADD COLUMN allow_full_size_viewing INTEGER;  -- NULL = use user default
ALTER TABLE images ADD COLUMN allow_downloads INTEGER;           -- NULL = use user default
```

#### Limitations
- Right-click protection is a "speed bump", not true DRM
- Browser DevTools can still access images
- Screenshots always possible
- Discourages casual copying, not determined theft

---

### Disable Right-Click Save from Gallery

**Status**: Not Started
**Priority**: Low
**Estimated Effort**: 1-2 hours
**Added**: 2025-11-11

#### Description
Add basic protection against casual right-click saving of images. This is a deterrent, not comprehensive security.

#### Implementation Options

**Option 1: CSS + JavaScript** (Recommended)
```css
.gallery-grid img, .lightbox img {
  user-select: none;
  -webkit-user-drag: none;
  pointer-events: none;
}
.gallery-item {
  pointer-events: auto;
}
```

```javascript
document.addEventListener('contextmenu', (e) => {
  if (e.target.tagName === 'IMG') {
    e.preventDefault();
    alert('Images are protected. Please contact the photographer for licensing.');
    return false;
  }
});
```

**Option 2: Transparent Overlay**
- Invisible div overlay on top of images intercepts clicks

**Option 3: Background Image** (NOT recommended)
- Breaks accessibility, lightbox libraries, not worth trade-off

#### Additional Measures
- Disable Ctrl+S / Cmd+S keyboard shortcuts
- DevTools detection (advanced, fragile, not recommended)
- **Watermarking** (most effective protection method)

#### Testing Checklist
- [ ] Right-click disabled on gallery images
- [ ] Right-click works on text/other elements
- [ ] Lightbox still functional
- [ ] Keyboard navigation works
- [ ] Mobile long-press handled
- [ ] Screen readers functional
- [ ] No console errors
