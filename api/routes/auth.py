"""
Authentication routes for Hensler Photography API

Provides JWT-based authentication with httpOnly cookies for secure session management.
"""

from fastapi import APIRouter, Request, Response, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from datetime import datetime, timedelta
import os
import bcrypt
import aiosqlite
import re
from typing import Optional

from api.database import DATABASE_PATH
from api.logging_config import get_logger
from api.rate_limit import limiter, RATE_LIMITS

# Initialize logger
logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/auth", tags=["authentication"])

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "INSECURE_DEV_KEY_CHANGE_IN_PRODUCTION")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Validate JWT secret key on module load
def _validate_jwt_secret():
    """Validate that JWT secret key is properly configured"""
    environment = os.getenv("ENVIRONMENT", "development")

    if not SECRET_KEY:
        raise ValueError(
            "CRITICAL SECURITY ERROR: JWT_SECRET_KEY environment variable is not set. "
            "Application cannot start without a secure JWT secret."
        )

    if SECRET_KEY == "INSECURE_DEV_KEY_CHANGE_IN_PRODUCTION":
        if environment == "production":
            raise ValueError(
                "CRITICAL SECURITY ERROR: JWT_SECRET_KEY is using insecure default value. "
                "You MUST set a secure random secret in production. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
            )
        else:
            logger.warning(
                "WARNING: Using insecure default JWT_SECRET_KEY in development. "
                "This is acceptable for local testing but NEVER use in production."
            )

    if len(SECRET_KEY) < 32:
        raise ValueError(
            f"CRITICAL SECURITY ERROR: JWT_SECRET_KEY is too short ({len(SECRET_KEY)} chars). "
            "Must be at least 32 characters for security. "
            "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )

# Run validation on module import
_validate_jwt_secret()


# User model (simple dict for now)
class User:
    def __init__(self, id: int, username: str, display_name: str, email: str, role: str):
        self.id = id
        self.username = username
        self.display_name = display_name
        self.email = email
        self.role = role


# Password validation and hashing functions
def validate_password(password: str) -> None:
    """
    Validate password complexity requirements.

    Requirements:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Raises HTTPException if validation fails.
    """
    if len(password) < 12:
        raise HTTPException(
            400,
            "Password must be at least 12 characters long"
        )

    if not re.search(r'[A-Z]', password):
        raise HTTPException(
            400,
            "Password must contain at least one uppercase letter"
        )

    if not re.search(r'[a-z]', password):
        raise HTTPException(
            400,
            "Password must contain at least one lowercase letter"
        )

    if not re.search(r'\d', password):
        raise HTTPException(
            400,
            "Password must contain at least one number"
        )

    if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\\/;~`]', password):
        raise HTTPException(
            400,
            "Password must contain at least one special character (!@#$%^&* etc.)"
        )

    # Check for common weak passwords
    common_passwords = {
        'Password123!', 'Welcome123!', 'Admin123!', 'Qwerty123!',
        'Letmein123!', 'Password1234!', 'Admin1234!', 'Test1234!'
    }
    if password in common_passwords:
        raise HTTPException(
            400,
            "This password is too common. Please choose a more unique password."
        )


def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    except Exception as e:
        logger.error(f"Password verification failed: {e}")
        return False


# Database helper functions
async def get_user_by_username(username: str) -> Optional[User]:
    """Fetch user from database by username"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute(
            """
            SELECT id, username, display_name, email, role, password_hash
            FROM users
            WHERE username = ?
            """,
            (username,)
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return User(
            id=row[0],
            username=row[1],
            display_name=row[2] or row[1],  # Fallback to username
            email=row[3],
            role=row[4]
        ), row[5]  # Return user and password_hash


async def get_user_by_id(user_id: int) -> Optional[User]:
    """Fetch user from database by ID"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        cursor = await db.execute(
            """
            SELECT id, username, display_name, email, role
            FROM users
            WHERE id = ?
            """,
            (user_id,)
        )
        row = await cursor.fetchone()

        if not row:
            return None

        return User(
            id=row[0],
            username=row[1],
            display_name=row[2] or row[1],
            email=row[3],
            role=row[4]
        )


# JWT token functions
def create_access_token(user: User) -> str:
    """Create a JWT access token for a user"""
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "exp": expire
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# Authentication dependency
async def get_current_user(request: Request) -> User:
    """
    FastAPI dependency that validates JWT token and returns current user.

    Raises HTTPException if not authenticated or token is invalid.
    """
    token = request.cookies.get("session_token")

    if not token:
        logger.warning(
            "Authentication failed: No session token",
            extra={"context": {"path": str(request.url.path)}}
        )
        raise HTTPException(
            status_code=401,
            detail="Not authenticated. Please log in.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    try:
        # Decode and validate token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")

        if user_id is None:
            raise HTTPException(401, "Invalid authentication token")

        # Load user from database
        user = await get_user_by_id(user_id)
        if user is None:
            raise HTTPException(401, "User not found")

        return user

    except JWTError as e:
        logger.warning(
            f"Authentication failed: Invalid JWT token: {e}",
            extra={"context": {"path": str(request.url.path)}}
        )
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired authentication token. Please log in again."
        )


# Optional authentication dependency (doesn't raise exception if not authenticated)
async def get_current_user_optional(request: Request) -> Optional[User]:
    """
    Optional authentication dependency - returns None if not authenticated.
    Useful for endpoints that work for both authenticated and anonymous users.
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


# Authentication routes

@router.post("/login")
@limiter.limit(RATE_LIMITS["auth_login"])
async def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...)
):
    """
    Authenticate user with username and password.

    Sets httpOnly session cookie on success.

    Rate limit: 5 attempts per minute per IP address to prevent brute force attacks.
    """
    logger.info(f"Login attempt for user: {username}")

    # Fetch user from database
    result = await get_user_by_username(username)

    if not result:
        logger.warning(f"Login failed: User not found: {username}")
        raise HTTPException(401, "Invalid username or password")

    user, password_hash = result

    # Verify password
    if not password_hash or not verify_password(password, password_hash):
        logger.warning(f"Login failed: Invalid password for user: {username}")
        raise HTTPException(401, "Invalid username or password")

    # Generate JWT token
    access_token = create_access_token(user)

    # Set httpOnly cookie
    response.set_cookie(
        key="session_token",
        value=access_token,
        httponly=True,
        secure=os.getenv("ENVIRONMENT") == "production",  # HTTPS only in production
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_HOURS * 3600  # seconds
    )

    logger.info(
        f"Login successful: {username} (role={user.role})",
        extra={
            "context": {
                "user_id": user.id,
                "username": username,
                "role": user.role
            }
        }
    )

    return {
        "success": True,
        "user": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "email": user.email,
            "role": user.role
        }
    }


@router.post("/logout")
async def logout(response: Response):
    """
    Log out the current user by clearing the session cookie.
    """
    response.delete_cookie(key="session_token")

    logger.info("User logged out")

    return {"success": True, "message": "Logged out successfully"}


@router.get("/me")
async def get_me(current_user: User = Depends(get_current_user)):
    """
    Get current authenticated user's information.
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "display_name": current_user.display_name,
        "email": current_user.email,
        "role": current_user.role
    }


@router.post("/register")
async def register(
    current_user: User = Depends(get_current_user),
    username: str = Form(...),
    email: str = Form(...),
    display_name: str = Form(...),
    password: str = Form(...),
    role: str = Form("photographer")
):
    """
    Create a new user account (admin only).
    """
    # Only admins can create users
    if current_user.role != "admin":
        raise HTTPException(403, "Only administrators can create new users")

    # Validate role
    if role not in ["admin", "photographer"]:
        raise HTTPException(400, "Invalid role. Must be 'admin' or 'photographer'")

    # Validate password complexity
    validate_password(password)

    # Hash password
    password_hash = hash_password(password)

    # Insert into database
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("PRAGMA foreign_keys = ON")
            await db.execute(
                """
                INSERT INTO users (username, email, display_name, role, password_hash)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, email, display_name, role, password_hash)
            )
            await db.commit()

        logger.info(
            f"User created: {username} (role={role})",
            extra={
                "context": {
                    "created_by": current_user.username,
                    "new_user": username,
                    "role": role
                }
            }
        )

        return {
            "success": True,
            "message": f"User '{username}' created successfully",
            "user": {
                "username": username,
                "email": email,
                "display_name": display_name,
                "role": role
            }
        }

    except aiosqlite.IntegrityError as e:
        logger.warning(f"User creation failed: {e}")
        raise HTTPException(400, "Username or email already exists")


@router.post("/change-password")
async def change_password(
    current_user: User = Depends(get_current_user),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...)
):
    """
    Change the current user's password.
    """
    # Verify passwords match
    if new_password != confirm_password:
        raise HTTPException(400, "New passwords do not match")

    # Validate new password complexity
    validate_password(new_password)

    # Fetch current password hash
    result = await get_user_by_username(current_user.username)
    if not result:
        raise HTTPException(404, "User not found")

    user, password_hash = result

    # Verify current password
    if not password_hash or not verify_password(current_password, password_hash):
        raise HTTPException(401, "Current password is incorrect")

    # Hash new password
    new_password_hash = hash_password(new_password)

    # Update database
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (new_password_hash, current_user.id)
        )
        await db.commit()

    logger.info(
        f"Password changed for user: {current_user.username}",
        extra={"context": {"user_id": current_user.id}}
    )

    return {
        "success": True,
        "message": "Password changed successfully"
    }
