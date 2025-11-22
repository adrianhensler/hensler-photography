"""
CSRF (Cross-Site Request Forgery) protection for Hensler Photography API

Implements token-based CSRF protection for all state-changing operations.
"""

from fastapi import Request, HTTPException, Depends
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
import os
from typing import Optional

from api.logging_config import get_logger

logger = get_logger(__name__)

# CSRF configuration
CSRF_SECRET_KEY = os.getenv("CSRF_SECRET_KEY", os.getenv("JWT_SECRET_KEY", "INSECURE_DEV_KEY"))
CSRF_TOKEN_EXPIRY = 3600  # 1 hour in seconds

# Token serializer
serializer = URLSafeTimedSerializer(CSRF_SECRET_KEY, salt="csrf-token")


def generate_csrf_token(session_data: Optional[str] = None) -> str:
    """
    Generate a CSRF token.

    Args:
        session_data: Optional session identifier to bind token to session

    Returns:
        URL-safe CSRF token string
    """
    # Use session data if provided, otherwise use a default value
    payload = session_data or "csrf-token"
    token = serializer.dumps(payload)
    logger.debug(f"Generated CSRF token for session: {session_data}")
    return token


def validate_csrf_token(token: str, session_data: Optional[str] = None) -> bool:
    """
    Validate a CSRF token.

    Args:
        token: The CSRF token to validate
        session_data: Optional session identifier to verify token binding

    Returns:
        True if valid, False otherwise
    """
    try:
        # Verify token signature and expiration
        payload = serializer.loads(token, max_age=CSRF_TOKEN_EXPIRY)

        # If session_data provided, verify it matches
        if session_data and payload != session_data:
            logger.warning(f"CSRF token session mismatch: expected {session_data}, got {payload}")
            return False

        return True

    except SignatureExpired:
        logger.warning("CSRF token expired")
        return False
    except BadSignature:
        logger.warning("CSRF token has invalid signature")
        return False
    except Exception as e:
        logger.error(f"CSRF token validation error: {e}")
        return False


def get_csrf_token_from_request(request: Request) -> Optional[str]:
    """
    Extract CSRF token from request (header or form data).

    Checks in order:
    1. X-CSRF-Token header
    2. csrf_token form field
    3. _csrf_token form field (alternative name)

    Args:
        request: FastAPI request object

    Returns:
        CSRF token string or None if not found
    """
    # Check header first (for AJAX requests)
    token = request.headers.get("X-CSRF-Token")
    if token:
        return token

    # Check form data (for HTML form submissions)
    # Note: This requires the request body to be consumed, which FastAPI handles
    return None  # Will be extracted from Form() in route handlers


async def verify_csrf_token(request: Request, csrf_token: str = None) -> str:
    """
    FastAPI dependency to verify CSRF token.

    Can be used as a dependency in route handlers:

    @router.post("/protected")
    async def protected_endpoint(
        csrf_token: str = Depends(verify_csrf_token),
        ...
    ):
        # Endpoint logic

    Args:
        request: FastAPI request object
        csrf_token: Optional token from form data

    Returns:
        The validated CSRF token

    Raises:
        HTTPException(403) if token is missing or invalid
    """
    # Try to get token from header first
    token = request.headers.get("X-CSRF-Token")

    # If not in header, use token from form data (if provided)
    if not token:
        token = csrf_token

    # If still no token, reject request
    if not token:
        logger.warning(
            "CSRF token missing",
            extra={"context": {"path": str(request.url.path), "method": request.method}},
        )
        raise HTTPException(
            status_code=403,
            detail="CSRF token missing. This request cannot be processed for security reasons.",
        )

    # Validate token
    # TODO: Bind to session when user is authenticated
    if not validate_csrf_token(token):
        logger.warning(
            "CSRF token invalid",
            extra={"context": {"path": str(request.url.path), "method": request.method}},
        )
        raise HTTPException(
            status_code=403,
            detail="CSRF token invalid or expired. Please refresh the page and try again.",
        )

    return token


def add_csrf_token_to_context(request: Request, context: dict) -> dict:
    """
    Helper to add CSRF token to template context.

    Usage:
        context = {"request": request, "user": user}
        context = add_csrf_token_to_context(request, context)
        return templates.TemplateResponse("page.html", context)

    Args:
        request: FastAPI request object
        context: Template context dictionary

    Returns:
        Updated context with csrf_token field
    """
    # Generate token bound to user session if authenticated
    session_token = request.cookies.get("session_token")
    csrf_token = generate_csrf_token(session_data=session_token)

    context["csrf_token"] = csrf_token
    return context
