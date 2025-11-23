# Password Reset Implementation Guide

**Status**: 🔴 Not Implemented (CLI Workaround Available)
**Priority**: LOW (family users) → HIGH (before non-family photographers)
**Estimated Effort**: 2-3 weeks (one developer)
**Cost**: $0 (SendGrid free tier)

---

## Quick Reference

### Current Password Security: ✅ EXCELLENT

Your passwords are **very well protected**:
- ✅ **bcrypt hashing** with 12 rounds (~200ms per password)
- ✅ **Unique salts** automatically generated per password
- ✅ **httpOnly cookies** prevent JavaScript access (XSS protection)
- ✅ **Rate limiting** (5 login attempts/minute) prevents brute force
- ✅ **Strong password policy** (12 char minimum, complexity required)
- ✅ **Audit logging** tracks all authentication events
- ✅ **HTTPS with TLS 1.3** encrypts all traffic

**No plaintext passwords are ever stored** - only bcrypt hashes.

### Current Gap: No Self-Service Password Reset

If a user forgets their password, admin must manually reset via CLI:

```bash
# SSH into VPS
cd /opt/prod/hensler_photography

# Reset password for a user
docker compose exec api python -m api.cli_utils set-password username "NewPassword123!"

# List all users first
docker compose exec api python -m api.cli_utils list-users
```

**Limitations**:
- Requires VPS SSH access
- Requires admin intervention
- Not scalable beyond family users
- Security gap: admin must securely communicate new password to user

**When This Matters**:
- ✅ **Now (family only)**: CLI workaround acceptable
- 🔴 **Future (non-family photographers)**: Self-service reset essential

---

## Implementation Overview

### What You'll Need

1. **Email Service**: SendGrid (free tier: 100 emails/day)
2. **Database Changes**: Add password reset token table
3. **API Endpoints**: 3 new routes for reset flow
4. **UI Components**: Forgot password link, reset forms
5. **Email Templates**: Reset link email, confirmation email
6. **Security Measures**: Rate limiting, token expiration, audit logging

### Implementation Phases

| Phase | Tasks | Time | Status |
|-------|-------|------|--------|
| **1. Email Infrastructure** | SendGrid setup, email service, templates | 3-4 days | ⏳ Not Started |
| **2. Database Schema** | Add reset token table, migration script | 2 days | ⏳ Not Started |
| **3. API Endpoints** | Request/verify/reset endpoints, validation | 4-5 days | ⏳ Not Started |
| **4. UI Implementation** | Forgot password link, reset forms | 3-4 days | ⏳ Not Started |
| **5. Testing** | Unit tests, integration tests, security tests | 3-4 days | ⏳ Not Started |
| **6. Documentation** | Update SECURITY_ARCHITECTURE.md, user guide | 1-2 days | ⏳ Not Started |

---

## Phase 1: Email Infrastructure

### SendGrid Setup (Recommended)

**Why SendGrid**:
- Free tier: 100 emails/day forever
- No credit card required for free tier
- Excellent deliverability (99%+ inbox rate)
- Simple API integration
- Industry standard

**Setup Steps**:

1. **Create SendGrid Account**
   - Go to: https://signup.sendgrid.com/
   - Sign up with your email
   - Verify your email address

2. **Create API Key**
   - Dashboard → Settings → API Keys
   - Click "Create API Key"
   - Name: "Hensler Photography Production"
   - Permissions: "Restricted Access" → "Mail Send" (full access)
   - Copy the API key (shown only once!)

3. **Verify Sender Identity**
   - Dashboard → Settings → Sender Authentication
   - Option A: Single Sender Verification (quick)
     - Verify `noreply@hensler.photography` or your email
   - Option B: Domain Authentication (better deliverability)
     - Add DNS records to hensler.photography domain
     - Proves you own the domain

4. **Add to Environment**
   ```bash
   # Add to .env or docker-compose.yml
   SENDGRID_API_KEY=SG.xxxxxxxxxxxxxxxxxxxxx
   SENDGRID_FROM_EMAIL=noreply@hensler.photography
   SENDGRID_FROM_NAME=Hensler Photography
   ```

### Email Service Implementation

**File**: `api/services/email.py` (create new file)

```python
"""Email sending service using SendGrid"""
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from api.logging_config import get_logger

logger = get_logger(__name__)

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
FROM_EMAIL = os.getenv("SENDGRID_FROM_EMAIL", "noreply@hensler.photography")
FROM_NAME = os.getenv("SENDGRID_FROM_NAME", "Hensler Photography")


async def send_password_reset_email(to_email: str, username: str, reset_token: str, subdomain: str = "adrian"):
    """
    Send password reset email with reset link.

    Args:
        to_email: Recipient email address
        username: User's username (for personalization)
        reset_token: Reset token (not hashed)
        subdomain: User's subdomain (adrian/liam)
    """
    if not SENDGRID_API_KEY:
        logger.error("SENDGRID_API_KEY not configured - cannot send email")
        raise ValueError("Email service not configured")

    # Build reset URL
    reset_url = f"https://{subdomain}.hensler.photography:4100/reset-password?token={reset_token}"

    # Create email content
    subject = "Reset your Hensler Photography password"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{
                display: inline-block;
                padding: 14px 28px;
                background: linear-gradient(135deg, #0066cc 0%, #0052a3 100%);
                color: white;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
            }}
            .footer {{ margin-top: 40px; color: #666; font-size: 14px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Reset Your Password</h1>
            <p>Hi {username},</p>
            <p>You requested to reset your password for your Hensler Photography account.</p>
            <p>Click the button below to create a new password:</p>
            <p style="margin: 30px 0;">
                <a href="{reset_url}" class="button">Reset Password</a>
            </p>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #0066cc;">{reset_url}</p>
            <p><strong>This link expires in 1 hour.</strong></p>
            <p>If you didn't request this password reset, please ignore this email. Your password will remain unchanged.</p>
            <div class="footer">
                <p>Hensler Photography<br>
                This is an automated message - please do not reply.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_content = f"""
    Reset Your Password

    Hi {username},

    You requested to reset your password for your Hensler Photography account.

    Click this link to create a new password:
    {reset_url}

    This link expires in 1 hour.

    If you didn't request this password reset, please ignore this email.

    ---
    Hensler Photography
    """

    # Send email via SendGrid
    try:
        message = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content),
            plain_text_content=Content("text/plain", text_content)
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        logger.info(
            f"Password reset email sent to {to_email}",
            extra={"context": {"username": username, "status_code": response.status_code}}
        )

        return True

    except Exception as e:
        logger.error(f"Failed to send password reset email: {str(e)}", exc_info=e)
        raise


async def send_password_changed_email(to_email: str, username: str):
    """
    Send confirmation email after password change.

    Args:
        to_email: Recipient email address
        username: User's username
    """
    if not SENDGRID_API_KEY:
        logger.error("SENDGRID_API_KEY not configured - cannot send email")
        return False

    subject = "Your password has been changed"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1>Password Changed Successfully</h1>
            <p>Hi {username},</p>
            <p>This confirms that your password has been changed successfully.</p>
            <p><strong>If you did not make this change</strong>, please contact us immediately at adrian@hensler.photography</p>
            <p>For security, we recommend:</p>
            <ul>
                <li>Using a unique password for your account</li>
                <li>Enabling two-factor authentication (coming soon)</li>
                <li>Keeping your email secure</li>
            </ul>
            <div style="margin-top: 40px; color: #666; font-size: 14px;">
                <p>Hensler Photography<br>
                This is an automated message - please do not reply.</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_content = f"""
    Password Changed Successfully

    Hi {username},

    This confirms that your password has been changed successfully.

    If you did not make this change, please contact us immediately.

    ---
    Hensler Photography
    """

    try:
        message = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content),
            plain_text_content=Content("text/plain", text_content)
        )

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        logger.info(
            f"Password changed confirmation sent to {to_email}",
            extra={"context": {"username": username}}
        )

        return True

    except Exception as e:
        logger.error(f"Failed to send password changed email: {str(e)}", exc_info=e)
        return False
```

### Add SendGrid Dependency

**File**: `api/requirements.txt`

```python
# Add this line
sendgrid==6.11.0
```

### Docker Compose Configuration

**File**: `docker-compose.yml`

```yaml
services:
  api:
    environment:
      # Add these lines
      - SENDGRID_API_KEY=${SENDGRID_API_KEY}
      - SENDGRID_FROM_EMAIL=noreply@hensler.photography
      - SENDGRID_FROM_NAME=Hensler Photography
```

---

## Phase 2: Database Schema

### Reset Token Table

**File**: `api/database.py`

Add this table to your schema:

```sql
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL,           -- SHA256 hash of reset token
    expires_at DATETIME NOT NULL,       -- Token valid for 1 hour
    used_at DATETIME,                   -- When token was used (NULL = unused)
    ip_address TEXT,                    -- IP that requested reset
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Index for fast token lookup
CREATE INDEX IF NOT EXISTS idx_reset_token_hash ON password_reset_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_reset_user_id ON password_reset_tokens(user_id);
```

### Migration Script

**File**: `api/migrations/add_password_reset.py` (create migrations folder)

```python
"""Add password reset tokens table"""
import aiosqlite
from api.database import DATABASE_PATH

async def migrate():
    """Add password_reset_tokens table"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Create table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL,
                expires_at DATETIME NOT NULL,
                used_at DATETIME,
                ip_address TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Create indexes
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_reset_token_hash
            ON password_reset_tokens(token_hash)
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_reset_user_id
            ON password_reset_tokens(user_id)
        """)

        await db.commit()
        print("✅ password_reset_tokens table created")

if __name__ == "__main__":
    import asyncio
    asyncio.run(migrate())
```

Run migration:
```bash
docker compose exec api python api/migrations/add_password_reset.py
```

---

## Phase 3: API Endpoints

### Pydantic Models

**File**: `api/models.py`

Add these models:

```python
class PasswordResetRequest(BaseModel):
    """Request password reset via email"""
    email: EmailStr = Field(..., description="Email address of user")


class PasswordResetVerify(BaseModel):
    """Verify reset token is valid"""
    token: str = Field(..., min_length=32, max_length=64)


class PasswordResetComplete(BaseModel):
    """Complete password reset with new password"""
    token: str = Field(..., min_length=32, max_length=64)
    new_password: str = Field(..., min_length=12)
    confirm_password: str = Field(..., min_length=12)

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v
```

### Authentication Routes

**File**: `api/routes/auth.py`

Add these endpoints:

```python
import secrets
import hashlib
from datetime import datetime, timedelta
from api.services.email import send_password_reset_email, send_password_changed_email


@router.post("/auth/request-reset")
@limiter.limit("3/hour")  # Strict rate limit to prevent abuse
async def request_password_reset(
    request: Request,
    reset_request: PasswordResetRequest
):
    """
    Request password reset email.

    Rate Limited: 3 requests per hour per IP address.

    Security:
    - Always returns success (prevents email enumeration)
    - Only sends email if user exists
    - Logs all requests for audit
    """
    email = reset_request.email.lower()
    client_ip = request.client.host if request.client else None

    # Audit log the request (even for non-existent emails)
    logger.info(
        f"Password reset requested for email: {email}",
        extra={"context": {"ip_address": client_ip}}
    )

    try:
        async with get_db_connection() as db:
            # Check if user exists
            cursor = await db.execute(
                "SELECT id, username, email, subdomain FROM users WHERE email = ?",
                (email,)
            )
            user = await cursor.fetchone()

            if user:
                user_id = user[0]
                username = user[1]
                subdomain = user[3] or "adrian"

                # Generate reset token (256-bit random)
                reset_token = secrets.token_urlsafe(32)

                # Hash token for storage (don't store plaintext)
                token_hash = hashlib.sha256(reset_token.encode()).hexdigest()

                # Token expires in 1 hour
                expires_at = datetime.utcnow() + timedelta(hours=1)

                # Invalidate any existing unused tokens for this user
                await db.execute(
                    "UPDATE password_reset_tokens SET used_at = CURRENT_TIMESTAMP WHERE user_id = ? AND used_at IS NULL",
                    (user_id,)
                )

                # Store new token
                await db.execute(
                    """INSERT INTO password_reset_tokens
                       (user_id, token_hash, expires_at, ip_address)
                       VALUES (?, ?, ?, ?)""",
                    (user_id, token_hash, expires_at, client_ip)
                )
                await db.commit()

                # Send email with reset link
                try:
                    await send_password_reset_email(email, username, reset_token, subdomain)

                    # Audit log successful email
                    await log_audit(
                        user_id=user_id,
                        action="auth.reset_requested",
                        ip_address=client_ip,
                        details={"email": email}
                    )
                except Exception as e:
                    logger.error(f"Failed to send reset email: {str(e)}")
                    # Don't reveal failure to user

            # Always return success (prevents email enumeration)
            return {
                "success": True,
                "message": "If that email exists, a reset link has been sent."
            }

    except Exception as e:
        logger.error(f"Password reset request failed: {str(e)}", exc_info=e)
        # Still return success to prevent enumeration
        return {
            "success": True,
            "message": "If that email exists, a reset link has been sent."
        }


@router.get("/auth/verify-reset-token")
async def verify_reset_token(token: str):
    """
    Verify if a reset token is valid.

    Returns username if valid, error if expired/invalid.
    Used by frontend to show appropriate UI.
    """
    try:
        # Hash the provided token
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        async with get_db_connection() as db:
            cursor = await db.execute("""
                SELECT
                    t.id, t.user_id, t.expires_at, t.used_at,
                    u.username, u.display_name
                FROM password_reset_tokens t
                JOIN users u ON t.user_id = u.id
                WHERE t.token_hash = ?
            """, (token_hash,))

            result = await cursor.fetchone()

            if not result:
                raise HTTPException(400, "Invalid reset token")

            token_id, user_id, expires_at, used_at, username, display_name = result

            # Check if already used
            if used_at:
                raise HTTPException(400, "Reset token has already been used")

            # Check if expired
            expires_datetime = datetime.fromisoformat(expires_at)
            if datetime.utcnow() > expires_datetime:
                raise HTTPException(400, "Reset token has expired")

            # Token is valid
            return {
                "valid": True,
                "username": username,
                "display_name": display_name
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}", exc_info=e)
        raise HTTPException(500, "Failed to verify token")


@router.post("/auth/reset-password")
@limiter.limit("5/hour")  # Allow few attempts in case of typos
async def reset_password(
    request: Request,
    reset: PasswordResetComplete
):
    """
    Reset password using valid token.

    Security:
    - Validates token (not expired, not used)
    - Validates new password complexity
    - Marks token as used (single-use)
    - Invalidates all other tokens for user
    - Sends confirmation email
    - Logs action for audit
    """
    client_ip = request.client.host if request.client else None

    try:
        # Validate password complexity
        validate_password(reset.new_password)

        # Hash the provided token
        token_hash = hashlib.sha256(reset.token.encode()).hexdigest()

        async with get_db_connection() as db:
            # Get token and user info
            cursor = await db.execute("""
                SELECT
                    t.id, t.user_id, t.expires_at, t.used_at,
                    u.username, u.email, u.display_name
                FROM password_reset_tokens t
                JOIN users u ON t.user_id = u.id
                WHERE t.token_hash = ?
            """, (token_hash,))

            result = await cursor.fetchone()

            if not result:
                raise HTTPException(400, "Invalid reset token")

            token_id, user_id, expires_at, used_at, username, email, display_name = result

            # Check if already used
            if used_at:
                raise HTTPException(400, "Reset token has already been used")

            # Check if expired
            expires_datetime = datetime.fromisoformat(expires_at)
            if datetime.utcnow() > expires_datetime:
                raise HTTPException(400, "Reset token has expired")

            # Hash new password
            new_password_hash = hash_password(reset.new_password)

            # Update password
            await db.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (new_password_hash, user_id)
            )

            # Mark this token as used
            await db.execute(
                "UPDATE password_reset_tokens SET used_at = CURRENT_TIMESTAMP WHERE id = ?",
                (token_id,)
            )

            # Invalidate all other unused tokens for this user
            await db.execute(
                "UPDATE password_reset_tokens SET used_at = CURRENT_TIMESTAMP WHERE user_id = ? AND id != ? AND used_at IS NULL",
                (user_id, token_id)
            )

            await db.commit()

            # Send confirmation email
            try:
                await send_password_changed_email(email, username)
            except Exception as e:
                logger.error(f"Failed to send confirmation email: {str(e)}")
                # Continue anyway - password was changed

            # Audit log
            await log_audit(
                user_id=user_id,
                action="auth.password_reset",
                ip_address=client_ip,
                details={"username": username}
            )

            logger.info(
                f"Password reset completed for user: {username}",
                extra={"context": {"user_id": user_id}}
            )

            return {
                "success": True,
                "message": "Password reset successful. You can now log in."
            }

    except HTTPException:
        raise
    except ValueError as e:
        # Password validation failed
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(f"Password reset failed: {str(e)}", exc_info=e)
        raise HTTPException(500, "Failed to reset password")
```

---

## Phase 4: UI Implementation

### Update Login Page

**File**: `api/templates/admin/login.html`

Add "Forgot Password?" link:

```html
<!-- Add after password input, before login button -->
<div style="text-align: right; margin-bottom: 20px;">
    <a href="/forgot-password" style="color: #0066cc; text-decoration: none; font-size: 14px;">
        Forgot Password?
    </a>
</div>
```

### Forgot Password Page

**File**: `api/templates/admin/forgot_password.html` (create new file)

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Forgot Password - Hensler Photography</title>
    <link rel="stylesheet" href="/static/css/variables.css">
    <style>
        body {
            background: linear-gradient(135deg, #0066cc 0%, #0052a3 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .container {
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 420px;
            padding: 48px 40px;
        }

        h1 {
            font-size: 28px;
            font-weight: 600;
            color: #1a1a1a;
            margin-bottom: 8px;
        }

        .description {
            font-size: 14px;
            color: #666;
            margin-bottom: 32px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            font-size: 14px;
            font-weight: 500;
            color: #333;
            margin-bottom: 8px;
        }

        .form-group input {
            width: 100%;
            padding: 12px 16px;
            font-size: 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            outline: none;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }

        .form-group input:focus {
            border-color: #0066cc;
            box-shadow: 0 0 0 3px rgba(0, 102, 204, 0.1);
        }

        .submit-button {
            width: 100%;
            padding: 14px;
            font-size: 16px;
            font-weight: 600;
            color: #fff;
            background: linear-gradient(135deg, #0066cc 0%, #0052a3 100%);
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .submit-button:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0, 102, 204, 0.3);
        }

        .submit-button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }

        .message {
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 14px;
            margin-bottom: 20px;
            display: none;
        }

        .message.success {
            background: #e6f4ea;
            color: #1e7e34;
            border-left: 4px solid #28a745;
        }

        .message.error {
            background: #fee;
            color: #c33;
            border-left: 4px solid #c33;
        }

        .message.show {
            display: block;
        }

        .back-link {
            text-align: center;
            margin-top: 24px;
            font-size: 14px;
        }

        .back-link a {
            color: #0066cc;
            text-decoration: none;
            font-weight: 500;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Forgot Password?</h1>
        <p class="description">Enter your email address and we'll send you a link to reset your password.</p>

        <div id="message" class="message"></div>

        <form id="forgot-form">
            <div class="form-group">
                <label for="email">Email Address</label>
                <input
                    type="email"
                    id="email"
                    name="email"
                    required
                    autofocus
                    autocomplete="email"
                    placeholder="your.email@example.com"
                >
            </div>

            <button type="submit" class="submit-button" id="submit-button">
                Send Reset Link
            </button>
        </form>

        <div class="back-link">
            <a href="/admin/login">← Back to Login</a>
        </div>
    </div>

    <script>
        const form = document.getElementById('forgot-form');
        const message = document.getElementById('message');
        const submitButton = document.getElementById('submit-button');

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            // Hide previous message
            message.classList.remove('show', 'success', 'error');

            // Disable button
            submitButton.disabled = true;
            submitButton.textContent = 'Sending...';

            const email = document.getElementById('email').value;

            try {
                const response = await fetch('/api/auth/request-reset', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ email })
                });

                const data = await response.json();

                if (response.ok) {
                    showMessage('success', 'If that email exists in our system, we\'ve sent a reset link. Check your inbox.');
                    form.reset();
                } else {
                    showMessage('error', data.detail || 'An error occurred. Please try again.');
                }
            } catch (error) {
                console.error('Request failed:', error);
                showMessage('error', 'Network error. Please try again.');
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = 'Send Reset Link';
            }
        });

        function showMessage(type, text) {
            message.textContent = text;
            message.classList.add('show', type);

            // Auto-hide after 10 seconds
            setTimeout(() => {
                message.classList.remove('show');
            }, 10000);
        }
    </script>
</body>
</html>
```

### Reset Password Page

**File**: `api/templates/admin/reset_password.html` (create new file)

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset Password - Hensler Photography</title>
    <link rel="stylesheet" href="/static/css/variables.css">
    <style>
        /* Use same styles as forgot_password.html */
        body {
            background: linear-gradient(135deg, #0066cc 0%, #0052a3 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }

        .container {
            background: #fff;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 420px;
            padding: 48px 40px;
        }

        /* ... rest of styles ... */
    </style>
</head>
<body>
    <div class="container">
        <div id="loading" style="text-align: center;">
            <p>Verifying reset link...</p>
        </div>

        <div id="invalid-token" style="display: none;">
            <h1>Invalid or Expired Link</h1>
            <p class="description">This password reset link is invalid or has expired. Please request a new one.</p>
            <a href="/forgot-password" class="submit-button" style="display: block; text-align: center; text-decoration: none;">
                Request New Link
            </a>
        </div>

        <div id="reset-form-container" style="display: none;">
            <h1>Reset Password</h1>
            <p class="description">Hi <strong id="username"></strong>, enter your new password below.</p>

            <div id="message" class="message"></div>

            <form id="reset-form">
                <div class="form-group">
                    <label for="new_password">New Password</label>
                    <input
                        type="password"
                        id="new_password"
                        name="new_password"
                        required
                        minlength="12"
                        autocomplete="new-password"
                    >
                    <small style="color: #666; font-size: 12px;">
                        Minimum 12 characters, must include uppercase, lowercase, number, and special character
                    </small>
                </div>

                <div class="form-group">
                    <label for="confirm_password">Confirm New Password</label>
                    <input
                        type="password"
                        id="confirm_password"
                        name="confirm_password"
                        required
                        minlength="12"
                        autocomplete="new-password"
                    >
                </div>

                <button type="submit" class="submit-button" id="submit-button">
                    Reset Password
                </button>
            </form>
        </div>
    </div>

    <script>
        // Get token from URL
        const params = new URLSearchParams(window.location.search);
        const token = params.get('token');

        const loading = document.getElementById('loading');
        const invalidToken = document.getElementById('invalid-token');
        const resetFormContainer = document.getElementById('reset-form-container');
        const usernameSpan = document.getElementById('username');
        const message = document.getElementById('message');
        const form = document.getElementById('reset-form');
        const submitButton = document.getElementById('submit-button');

        // Verify token on page load
        if (!token) {
            loading.style.display = 'none';
            invalidToken.style.display = 'block';
        } else {
            verifyToken();
        }

        async function verifyToken() {
            try {
                const response = await fetch(`/api/auth/verify-reset-token?token=${encodeURIComponent(token)}`);
                const data = await response.json();

                loading.style.display = 'none';

                if (response.ok && data.valid) {
                    usernameSpan.textContent = data.display_name || data.username;
                    resetFormContainer.style.display = 'block';
                } else {
                    invalidToken.style.display = 'block';
                }
            } catch (error) {
                console.error('Token verification failed:', error);
                loading.style.display = 'none';
                invalidToken.style.display = 'block';
            }
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            message.classList.remove('show', 'success', 'error');

            const newPassword = document.getElementById('new_password').value;
            const confirmPassword = document.getElementById('confirm_password').value;

            if (newPassword !== confirmPassword) {
                showMessage('error', 'Passwords do not match');
                return;
            }

            submitButton.disabled = true;
            submitButton.textContent = 'Resetting...';

            try {
                const response = await fetch('/api/auth/reset-password', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        token: token,
                        new_password: newPassword,
                        confirm_password: confirmPassword
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    showMessage('success', 'Password reset successful! Redirecting to login...');
                    setTimeout(() => {
                        window.location.href = '/admin/login';
                    }, 2000);
                } else {
                    showMessage('error', data.detail || 'Password reset failed. Please try again.');
                    submitButton.disabled = false;
                    submitButton.textContent = 'Reset Password';
                }
            } catch (error) {
                console.error('Reset failed:', error);
                showMessage('error', 'Network error. Please try again.');
                submitButton.disabled = false;
                submitButton.textContent = 'Reset Password';
            }
        });

        function showMessage(type, text) {
            message.textContent = text;
            message.classList.add('show', type);
        }
    </script>
</body>
</html>
```

### Add Page Routes

**File**: `api/main.py`

Add these routes:

```python
@app.get("/forgot-password")
async def forgot_password_page(request: Request):
    """Forgot password form page (public)"""
    return templates.TemplateResponse("admin/forgot_password.html", {"request": request})

@app.get("/reset-password")
async def reset_password_page(request: Request):
    """Reset password form page (public)"""
    return templates.TemplateResponse("admin/reset_password.html", {"request": request})
```

---

## Phase 5: Testing

### Unit Tests

**File**: `tests/test_password_reset.py` (create new file)

```python
"""Unit tests for password reset functionality"""
import pytest
from datetime import datetime, timedelta
import hashlib

@pytest.mark.asyncio
async def test_request_password_reset_valid_email(client):
    """Test requesting reset for valid email"""
    response = await client.post("/api/auth/request-reset", json={
        "email": "adrian@hensler.photography"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

@pytest.mark.asyncio
async def test_request_password_reset_invalid_email(client):
    """Test requesting reset for non-existent email (should still return success)"""
    response = await client.post("/api/auth/request-reset", json={
        "email": "nonexistent@example.com"
    })
    assert response.status_code == 200  # Don't reveal if email exists
    data = response.json()
    assert data["success"] is True

@pytest.mark.asyncio
async def test_verify_valid_token(client, db):
    """Test verifying a valid reset token"""
    # Create a reset token
    token = "test_token_123"
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.utcnow() + timedelta(hours=1)

    await db.execute("""
        INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
        VALUES (1, ?, ?)
    """, (token_hash, expires_at))
    await db.commit()

    response = await client.get(f"/api/auth/verify-reset-token?token={token}")
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert "username" in data

@pytest.mark.asyncio
async def test_verify_expired_token(client, db):
    """Test verifying an expired reset token"""
    token = "expired_token_123"
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.utcnow() - timedelta(hours=1)  # Expired

    await db.execute("""
        INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
        VALUES (1, ?, ?)
    """, (token_hash, expires_at))
    await db.commit()

    response = await client.get(f"/api/auth/verify-reset-token?token={token}")
    assert response.status_code == 400
    assert "expired" in response.json()["detail"].lower()

@pytest.mark.asyncio
async def test_reset_password_success(client, db):
    """Test successfully resetting password"""
    # Create valid token
    token = "valid_reset_token"
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.utcnow() + timedelta(hours=1)

    await db.execute("""
        INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
        VALUES (1, ?, ?)
    """, (token_hash, expires_at))
    await db.commit()

    # Reset password
    response = await client.post("/api/auth/reset-password", json={
        "token": token,
        "new_password": "NewSecurePass123!",
        "confirm_password": "NewSecurePass123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Verify token is now marked as used
    cursor = await db.execute(
        "SELECT used_at FROM password_reset_tokens WHERE token_hash = ?",
        (token_hash,)
    )
    result = await cursor.fetchone()
    assert result[0] is not None  # used_at should be set

@pytest.mark.asyncio
async def test_reset_password_weak_password(client, db):
    """Test resetting with weak password (should fail validation)"""
    token = "valid_token"
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.utcnow() + timedelta(hours=1)

    await db.execute("""
        INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
        VALUES (1, ?, ?)
    """, (token_hash, expires_at))
    await db.commit()

    response = await client.post("/api/auth/reset-password", json={
        "token": token,
        "new_password": "weak",  # Too short, no complexity
        "confirm_password": "weak"
    })
    assert response.status_code == 400

@pytest.mark.asyncio
async def test_token_single_use(client, db):
    """Test that reset tokens can only be used once"""
    token = "single_use_token"
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.utcnow() + timedelta(hours=1)

    await db.execute("""
        INSERT INTO password_reset_tokens (user_id, token_hash, expires_at)
        VALUES (1, ?, ?)
    """, (token_hash, expires_at))
    await db.commit()

    # First use - should succeed
    response1 = await client.post("/api/auth/reset-password", json={
        "token": token,
        "new_password": "FirstPassword123!",
        "confirm_password": "FirstPassword123!"
    })
    assert response1.status_code == 200

    # Second use - should fail
    response2 = await client.post("/api/auth/reset-password", json={
        "token": token,
        "new_password": "SecondPassword123!",
        "confirm_password": "SecondPassword123!"
    })
    assert response2.status_code == 400
    assert "already been used" in response2.json()["detail"].lower()
```

### Integration Tests

Test the full flow:
1. User requests password reset
2. Email is sent (mock email service)
3. User clicks reset link
4. Token is verified
5. Password is changed
6. Confirmation email sent
7. User can log in with new password

### Security Tests

- Rate limiting (>3 requests/hour blocked)
- Token expiration (1 hour)
- Token reuse prevention
- Weak password rejection
- SQL injection attempts
- Email enumeration prevention

---

## Phase 6: Documentation Updates

### Update SECURITY_ARCHITECTURE.md

Remove line 289-296 (password reset gap) and add:

```markdown
### Password Reset (Implemented)

**Mechanism**: Email-based reset with time-limited tokens

**Security Features**:
- 256-bit random tokens (cryptographically secure)
- SHA256 hashed tokens in database (no plaintext)
- 1-hour token expiration
- Single-use tokens (prevents replay attacks)
- Rate limiting (3 requests/hour per IP)
- Audit logging (all requests tracked)
- Email enumeration prevention (always return success)
- Weak password rejection
- Confirmation email after password change

**Rate Limits**:
- Reset request: 3 per hour per IP address
- Reset completion: 5 per hour per IP address

**Token Lifecycle**:
1. User requests reset → token generated and hashed
2. Email sent with plaintext token in URL
3. User clicks link → token verified (not expired, not used)
4. User sets new password → token marked as used
5. All other unused tokens for user invalidated
```

### Update User Documentation

Create user guide explaining:
- How to reset password if forgotten
- What to do if you don't receive reset email
- How long reset links are valid
- Security best practices

---

## Security Checklist

Before deploying password reset to production:

### Email Security
- [ ] SendGrid account created and verified
- [ ] Sender identity verified (single sender or domain)
- [ ] API key stored securely (not in git)
- [ ] FROM email address set to noreply@hensler.photography
- [ ] Test email delivery (check spam folder)

### Token Security
- [ ] Tokens generated with `secrets.token_urlsafe(32)` (256-bit)
- [ ] Tokens stored as SHA256 hashes (not plaintext)
- [ ] Token expiration set to 1 hour
- [ ] Single-use tokens enforced (marked as used)
- [ ] Old tokens invalidated on new request

### Rate Limiting
- [ ] Reset request limited to 3/hour per IP
- [ ] Reset completion limited to 5/hour per IP
- [ ] Rate limit headers included in responses

### Validation
- [ ] Email format validated (Pydantic EmailStr)
- [ ] New password complexity validated (12 char, uppercase, lowercase, digit, special)
- [ ] Password confirmation matches
- [ ] Token format validated (32-64 characters)

### Audit Logging
- [ ] All reset requests logged (even invalid emails)
- [ ] All password changes logged
- [ ] IP addresses recorded for forensics
- [ ] Token usage logged (success/failure)

### Email Enumeration Prevention
- [ ] Same success message for valid and invalid emails
- [ ] No timing differences in responses
- [ ] Rate limiting prevents bulk enumeration

### User Experience
- [ ] Clear error messages (without revealing security details)
- [ ] Helpful instructions ("Check your email")
- [ ] Link expiration clearly communicated
- [ ] Confirmation email sent after password change

### Testing
- [ ] Unit tests pass (token generation, validation, expiration)
- [ ] Integration tests pass (full reset flow)
- [ ] Security tests pass (rate limiting, token reuse, weak passwords)
- [ ] Email delivery tested (dev and prod environments)

---

## Deployment Instructions

### Development Environment

1. **Install Dependencies**
   ```bash
   cd /opt/dev/hensler_photography
   docker compose down
   docker compose build
   ```

2. **Run Database Migration**
   ```bash
   docker compose up -d
   docker compose exec api python api/migrations/add_password_reset.py
   ```

3. **Set Environment Variables**
   ```bash
   # Add to .env file
   echo "SENDGRID_API_KEY=SG.your_key_here" >> .env
   echo "SENDGRID_FROM_EMAIL=noreply@hensler.photography" >> .env
   ```

4. **Test Email Sending**
   ```bash
   docker compose exec api python -c "
   import asyncio
   from api.services.email import send_password_reset_email
   asyncio.run(send_password_reset_email(
       'your.email@example.com',
       'testuser',
       'test_token_123',
       'adrian'
   ))
   "
   ```

5. **Test Full Flow**
   - Go to http://localhost:4100/admin/login
   - Click "Forgot Password?"
   - Enter your email
   - Check inbox for reset email
   - Click reset link
   - Set new password
   - Log in with new password

### Production Deployment

1. **Backup Database**
   ```bash
   cd /opt/prod/hensler_photography
   docker compose exec api sqlite3 /data/gallery.db ".backup '/data/backup_$(date +%Y%m%d).db'"
   ```

2. **Pull Latest Code**
   ```bash
   git pull origin main
   ```

3. **Run Migration**
   ```bash
   docker compose exec api python api/migrations/add_password_reset.py
   ```

4. **Set Production Environment Variables**
   ```bash
   # Edit docker-compose.yml or use .env file
   # DO NOT commit SendGrid API key to git!
   ```

5. **Restart API Container**
   ```bash
   docker compose restart api
   ```

6. **Verify Health**
   ```bash
   curl https://adrian.hensler.photography:4100/api/health
   ```

7. **Test Password Reset Flow**
   - Use actual photographer email addresses
   - Verify emails arrive (check spam)
   - Complete full reset flow
   - Verify audit logs

---

## Monitoring and Maintenance

### Audit Log Queries

```sql
-- View recent password reset requests
SELECT
    u.username,
    t.created_at,
    t.expires_at,
    t.used_at,
    t.ip_address
FROM password_reset_tokens t
JOIN users u ON t.user_id = u.id
ORDER BY t.created_at DESC
LIMIT 20;

-- Count reset requests by user (detect abuse)
SELECT
    u.username,
    COUNT(*) as reset_count
FROM password_reset_tokens t
JOIN users u ON t.user_id = u.id
WHERE t.created_at > datetime('now', '-7 days')
GROUP BY u.username
ORDER BY reset_count DESC;

-- View failed reset attempts (audit log)
SELECT
    action,
    details,
    ip_address,
    timestamp
FROM audit_log
WHERE action LIKE '%reset%'
ORDER BY timestamp DESC
LIMIT 50;
```

### Email Delivery Monitoring

Check SendGrid dashboard:
- Opens/Clicks tracking
- Bounce rate (bad email addresses)
- Spam complaints
- Delivery rate

### Common Issues

**Issue**: Reset emails not arriving
- Check spam folder
- Verify sender identity in SendGrid
- Check SendGrid activity log
- Verify SENDGRID_API_KEY is set

**Issue**: "Rate limit exceeded" errors
- Normal if user clicks multiple times
- May indicate abuse if frequent
- Check IP address in audit logs

**Issue**: "Token expired" errors
- User took >1 hour to click link
- Instruct user to request new reset
- Consider extending to 2 hours if common

**Issue**: "Token already used" errors
- User clicked link twice
- Security feature working correctly
- Instruct user to request new reset

---

## Future Enhancements

### Priority: Medium
- [ ] **Two-Factor Authentication (2FA)**: Add TOTP support for extra security
- [ ] **Security Questions**: Backup recovery method if email unavailable
- [ ] **Account Lockout**: Lock account after N failed login attempts
- [ ] **Password History**: Prevent reusing last N passwords
- [ ] **Breach Detection**: Check passwords against Have I Been Pwned API

### Priority: Low
- [ ] **Magic Link Login**: Passwordless authentication via email
- [ ] **Social Login**: Google/GitHub OAuth integration
- [ ] **Password Strength Meter**: Real-time feedback on client-side
- [ ] **Geolocation Alerts**: Notify on login from unusual location
- [ ] **Device Management**: View/revoke sessions from different devices

---

## References

**Internal Documentation**:
- `SECURITY_ARCHITECTURE.md` - Overall security design (identifies this gap)
- `api/routes/auth.py` - Current authentication implementation
- `api/cli_utils.py` - CLI password management tools
- `api/audit.py` - Audit logging functions

**External Resources**:
- [OWASP Password Reset Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)
- [NIST 800-63B Digital Identity Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)
- [SendGrid API Documentation](https://docs.sendgrid.com/)
- [bcrypt Best Practices](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-15
**Author**: Claude Code (Anthropic)
**Status**: Ready for Implementation
