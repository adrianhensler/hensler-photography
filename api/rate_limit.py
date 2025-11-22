"""
Rate limiting configuration for Hensler Photography API

Prevents brute force attacks and API abuse by limiting request rates.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Global rate limiter instance
# Can be imported and used across the application
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # Default: 100 requests per minute per IP
    storage_uri="memory://",  # Use in-memory storage (simple, fast)
)

# Rate limit presets for different endpoint types
RATE_LIMITS = {
    "auth_login": "5/minute",  # Very strict for login attempts
    "auth_register": "3/hour",  # Strict for user registration
    "auth_change_password": "5/hour",  # Moderate for password changes
    "api_general": "100/minute",  # General API endpoints
    "upload": "20/hour",  # Image upload rate limit
}
