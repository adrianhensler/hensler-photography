# Google OAuth Implementation - Shelved for Later

**Status**: Database ready, implementation paused for Phase 4
**Estimated Remaining Time**: 20-30 minutes of coding + 10 minutes setup

---

## ✅ Completed (Sprint 4 Phase 3b - Partial)

### Database Migration
- **File**: `api/migrations/002_add_google_oauth.py`
- **Changes**:
  - Added `google_id` column to users table (stores Google user ID)
  - Added `auth_method` column ('password' or 'google')
  - Created unique index: `idx_users_google_id`
- **Status**: ✅ Migration run successfully

### Dependencies
- **Installed**: `authlib==1.3.0` in `requirements.txt`
- **Status**: ✅ Docker image rebuilt with authlib

---

## 📋 Remaining Work

### 1. Google Cloud Console Setup (10 minutes)

**Steps**:
1. Go to: https://console.cloud.google.com/apis/credentials
2. Create a new project (or use existing): "Hensler Photography"
3. Enable Google+ API (for user profile access)
4. Create OAuth 2.0 Client ID:
   - Application type: Web application
   - Name: "Hensler Photography Admin"
   - Authorized JavaScript origins:
     - `https://hensler.photography:4100`
     - `http://localhost:4100` (for dev testing)
   - Authorized redirect URIs:
     - `https://hensler.photography:4100/api/auth/google/callback`
     - `http://localhost:4100/api/auth/google/callback` (for dev)
5. Copy Client ID and Client Secret

**Environment Variables** (add to `.env` or docker-compose):
```bash
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
```

---

### 2. Implement Google OAuth Routes (15-20 minutes)

**File**: `api/routes/auth.py`

**Add these routes**:

```python
from authlib.integrations.starlette_client import OAuth
import os

# Initialize OAuth
oauth = OAuth()
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

@router.get("/google/login")
async def google_login(request: Request):
    """Redirect to Google OAuth consent screen"""
    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@router.get("/google/callback")
async def google_callback(request: Request, response: Response):
    """Handle Google OAuth callback"""
    try:
        # Exchange authorization code for access token
        token = await oauth.google.authorize_access_token(request)

        # Get user info from Google
        user_info = token.get('userinfo')
        google_id = user_info.get('sub')  # Google's unique user ID
        email = user_info.get('email')
        name = user_info.get('name')

        # Check if user exists by google_id
        user = await get_user_by_google_id(google_id)

        if not user:
            # Try to link by email (for existing users)
            user = await get_user_by_email(email)

            if user:
                # Link Google account to existing user
                await link_google_account(user.id, google_id)
                logger.info(f"Linked Google account to existing user: {user.username}")
            else:
                # Email not recognized - deny access
                logger.warning(f"Google login attempt with unrecognized email: {email}")
                raise HTTPException(403, f"No account found for {email}. Contact administrator.")

        # Generate JWT token (same as password login)
        access_token = create_access_token(user)

        # Set httpOnly cookie
        response.set_cookie(
            key="session_token",
            value=access_token,
            httponly=True,
            secure=os.getenv("ENVIRONMENT") == "production",
            samesite="lax",
            max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600
        )

        logger.info(f"Google login successful: {user.username} ({email})")

        # Redirect to admin dashboard
        return RedirectResponse(url="/admin", status_code=303)

    except Exception as e:
        logger.error(f"Google OAuth callback error: {e}")
        return RedirectResponse(url="/admin/login?error=oauth_failed", status_code=303)


# Helper functions to add
async def get_user_by_google_id(google_id: str) -> Optional[User]:
    """Fetch user by Google ID"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT id, username, display_name, email, role FROM users WHERE google_id = ?",
            (google_id,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return User(id=row[0], username=row[1], display_name=row[2], email=row[3], role=row[4])

async def get_user_by_email(email: str) -> Optional[User]:
    """Fetch user by email"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT id, username, display_name, email, role FROM users WHERE email = ?",
            (email,)
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return User(id=row[0], username=row[1], display_name=row[2], email=row[3], role=row[4])

async def link_google_account(user_id: int, google_id: str):
    """Link Google account to existing user"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "UPDATE users SET google_id = ?, auth_method = 'google' WHERE id = ?",
            (google_id, user_id)
        )
        await db.commit()
```

---

### 3. Update Login Page (5 minutes)

**File**: `api/templates/admin/login.html`

**Add Google Sign-In button** (add below password field, before login button):

```html
<div style="text-align: center; margin: 20px 0;">
    <div style="color: #999; font-size: 14px; margin-bottom: 16px;">or</div>
</div>

<a href="/api/auth/google/login" class="google-button">
    <svg width="18" height="18" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48">
        <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
        <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
        <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
        <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
    </svg>
    Sign in with Google
</a>
```

**Add CSS** (in `<style>` section):

```css
.google-button {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    width: 100%;
    padding: 12px;
    font-size: 15px;
    font-weight: 500;
    color: #333;
    background: #fff;
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    text-decoration: none;
    transition: all 0.2s ease;
}

.google-button:hover {
    background: #f8f8f8;
    border-color: #ccc;
}

.google-button svg {
    flex-shrink: 0;
}
```

---

## 🔒 Security Considerations

### Auto-Linking by Email
**Current Design**: Automatically link Google accounts to existing users by email match.

**Emails that will auto-link**:
- `adrianhensler@gmail.com` → `adrian` (admin)
- `liamhensler@gmail.com` → `liam` (photographer)

**Security Notes**:
- ✅ Safe because Google verifies email ownership
- ✅ Only these 2 emails exist in database (controlled environment)
- ✅ No public registration (admin-only user creation)
- ⚠️ If you add more users later, ensure their emails match what they'll use with Google

### Alternative: Manual Linking
If you prefer explicit linking instead of auto-linking:
1. User logs in with password first
2. Settings page has "Link Google Account" button
3. Redirects to Google OAuth
4. Links google_id to current user

---

## 📊 Testing Plan (When Implemented)

### Test Cases

**1. First-time Google login (Adrian)**:
- Click "Sign in with Google"
- Choose adrianhensler@gmail.com
- Should auto-link to existing `adrian` user
- Should redirect to admin dashboard
- Should see "Adrian Hensler (admin)" in header

**2. First-time Google login (Liam)**:
- Click "Sign in with Google"
- Choose liamhensler@gmail.com
- Should auto-link to existing `liam` user
- Should redirect to admin dashboard (or /manage when implemented)

**3. Unrecognized email**:
- Try signing in with random@gmail.com
- Should show error: "No account found for random@gmail.com. Contact administrator."
- Should NOT create new user

**4. Return visit**:
- After linking once, subsequent logins should be instant
- No password needed

**5. Dual auth methods**:
- After linking Google, can still log in with username/password
- Both methods work for same account

---

## 📝 Future Enhancements

### Phase 1 (Current Scope)
- ✅ Google OAuth login
- ✅ Auto-link by email
- ✅ Same permissions as password login

### Phase 2 (Future)
- Add "Unlink Google Account" in user settings
- Show auth method in admin dashboard ("Password" or "Google")
- Allow users without passwords (Google-only accounts)

### Phase 3 (Future)
- Add more OAuth providers (GitHub, Microsoft)
- Remember provider preference (show "Continue with Google" if user used it before)

---

## 🐛 Troubleshooting

### "redirect_uri_mismatch" error
- Check Google Console authorized redirect URIs match exactly
- Must include protocol (https://) and port (:4100)
- Dev and prod URIs must both be added

### "access_denied" when clicking Google button
- Check GOOGLE_CLIENT_ID is set correctly
- Check OAuth consent screen is configured
- Check user email is from allowed domain (if restricted)

### User logs in but gets 403 error
- Email doesn't match any user in database
- Check user's email in database: `SELECT email FROM users;`
- Either update user's email or ask user to use different Google account

---

## 📁 Files Modified (Ready for Commit)

When we complete this later:
- ✅ `api/migrations/002_add_google_oauth.py` (created, run)
- ✅ `api/requirements.txt` (authlib added)
- ⏳ `api/routes/auth.py` (add Google routes)
- ⏳ `api/templates/admin/login.html` (add Google button)
- ⏳ `docker-compose.local.yml` (add GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET env vars)
- ⏳ `.env` file (add credentials - NOT committed to git)

---

**Created**: 2025-11-02
**Status**: Shelved for Phase 4 (Photographer Dashboards)
**Resume After**: Phase 4 complete, ready for polish features
