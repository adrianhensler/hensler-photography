"""Shared security utilities for environment secret validation."""

import os


def require_env_secret(var_name: str, *, min_length: int = 32) -> str:
    """Return a required secret from environment variables.

    Raises:
        ValueError: If the environment variable is missing or does not meet length requirements.
    """
    secret = os.getenv(var_name)

    if not secret:
        raise ValueError(
            f"CRITICAL SECURITY ERROR: {var_name} environment variable is not set. "
            "Application cannot start without this secret."
        )

    if len(secret) < min_length:
        raise ValueError(
            "CRITICAL SECURITY ERROR: "
            f"{var_name} is too short ({len(secret)} chars). "
            f"Must be at least {min_length} characters for security. "
            "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(32))'"
        )

    return secret


# Cache validated secrets at module import to ensure application fails fast
JWT_SECRET_KEY = require_env_secret("JWT_SECRET_KEY")
CSRF_SECRET_KEY = require_env_secret("CSRF_SECRET_KEY")


def get_jwt_secret_key() -> str:
    """Return the validated JWT secret key."""
    return JWT_SECRET_KEY


def get_csrf_secret_key() -> str:
    """Return the secret key to use for CSRF protection.

    Enforces that a dedicated CSRF secret is configured and long enough.
    """
    return CSRF_SECRET_KEY
