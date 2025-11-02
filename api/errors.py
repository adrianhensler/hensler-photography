"""
Structured Error Response System for Hensler Photography API

Provides consistent, machine-readable error responses for both human users and AI assistants.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class ErrorCode(str, Enum):
    """Standard error codes for the API"""

    # Authentication & Authorization
    AUTH_MISSING_KEY = "AUTH_MISSING_KEY"
    AUTH_INVALID_KEY = "AUTH_INVALID_KEY"

    # Rate Limiting
    RATE_CLAUDE_LIMIT = "RATE_CLAUDE_LIMIT"
    RATE_STORAGE_QUOTA = "RATE_STORAGE_QUOTA"

    # Validation Errors
    VALIDATION_FILE_TOO_LARGE = "VALIDATION_FILE_TOO_LARGE"
    VALIDATION_INVALID_TYPE = "VALIDATION_INVALID_TYPE"
    VALIDATION_CORRUPT_IMAGE = "VALIDATION_CORRUPT_IMAGE"
    VALIDATION_MISSING_FIELD = "VALIDATION_MISSING_FIELD"

    # Processing Errors
    PROCESSING_IMAGE_FAILED = "PROCESSING_IMAGE_FAILED"
    PROCESSING_EXIF_FAILED = "PROCESSING_EXIF_FAILED"
    PROCESSING_VARIANT_FAILED = "PROCESSING_VARIANT_FAILED"
    PROCESSING_AI_FAILED = "PROCESSING_AI_FAILED"

    # Database Errors
    DATABASE_CONNECTION_FAILED = "DATABASE_CONNECTION_FAILED"
    DATABASE_CONSTRAINT_VIOLATION = "DATABASE_CONSTRAINT_VIOLATION"
    DATABASE_NOT_FOUND = "DATABASE_NOT_FOUND"

    # External API Errors
    EXTERNAL_CLAUDE_ERROR = "EXTERNAL_CLAUDE_ERROR"
    EXTERNAL_CLAUDE_TIMEOUT = "EXTERNAL_CLAUDE_TIMEOUT"
    EXTERNAL_CLAUDE_INVALID_MODEL = "EXTERNAL_CLAUDE_INVALID_MODEL"

    # Generic
    INTERNAL_ERROR = "INTERNAL_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class ErrorSeverity(str, Enum):
    """Error severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorResponse:
    """Structured error response for API endpoints"""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        user_message: str,
        http_status: int = 500,
        suggestion: Optional[str] = None,
        docs_url: Optional[str] = None,
        retry: bool = False,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Optional[Dict[str, Any]] = None,
        stack_trace: Optional[str] = None
    ):
        self.code = code
        self.message = message
        self.user_message = user_message
        self.http_status = http_status
        self.suggestion = suggestion
        self.docs_url = docs_url
        self.retry = retry
        self.severity = severity
        self.context = context or {}
        self.stack_trace = stack_trace
        self.timestamp = datetime.utcnow().isoformat() + "Z"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        error_dict = {
            "success": False,
            "error": {
                "code": self.code.value,
                "message": self.message,
                "user_message": self.user_message,
                "timestamp": self.timestamp,
                "details": {
                    "severity": self.severity.value,
                    "retry": self.retry
                },
                "context": self.context
            }
        }

        if self.suggestion:
            error_dict["error"]["details"]["suggestion"] = self.suggestion

        if self.docs_url:
            error_dict["error"]["details"]["docs_url"] = self.docs_url

        if self.stack_trace:
            error_dict["error"]["details"]["stack_trace"] = self.stack_trace

        return error_dict

    def to_log_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for structured logging"""
        return {
            "timestamp": self.timestamp,
            "level": self.severity.value.upper(),
            "error_code": self.code.value,
            "message": self.message,
            "context": self.context,
            "stack_trace": self.stack_trace
        }


# Common error constructors

def missing_api_key_error(context: Optional[Dict[str, Any]] = None) -> ErrorResponse:
    """Error when ANTHROPIC_API_KEY is not configured"""
    return ErrorResponse(
        code=ErrorCode.AUTH_MISSING_KEY,
        message="Claude API key not configured",
        user_message="AI-powered captions are currently unavailable. Your photos will still be uploaded with basic metadata.",
        http_status=503,
        suggestion="Set the ANTHROPIC_API_KEY environment variable in your docker-compose.yml file",
        docs_url="https://docs.anthropic.com/api/getting-started",
        retry=False,
        severity=ErrorSeverity.WARNING,
        context=context
    )


def invalid_api_key_error(context: Optional[Dict[str, Any]] = None) -> ErrorResponse:
    """Error when API key is invalid"""
    return ErrorResponse(
        code=ErrorCode.AUTH_INVALID_KEY,
        message="Claude API key is invalid",
        user_message="AI captions failed - API key appears to be invalid. Please check your configuration.",
        http_status=401,
        suggestion="Verify your ANTHROPIC_API_KEY is correct",
        docs_url="https://docs.anthropic.com/api/getting-started",
        retry=False,
        severity=ErrorSeverity.ERROR,
        context=context
    )


def rate_limit_error(retry_after: int = 60, context: Optional[Dict[str, Any]] = None) -> ErrorResponse:
    """Error when Claude API rate limit is hit"""
    return ErrorResponse(
        code=ErrorCode.RATE_CLAUDE_LIMIT,
        message="Claude API rate limit exceeded",
        user_message=f"AI service is temporarily rate limited. Please wait {retry_after} seconds and try again.",
        http_status=429,
        suggestion=f"Wait {retry_after} seconds before retrying, or upgrade your API plan for higher limits",
        docs_url="https://docs.anthropic.com/api/rate-limits",
        retry=True,
        severity=ErrorSeverity.WARNING,
        context={**(context or {}), "retry_after_seconds": retry_after}
    )


def file_too_large_error(file_size: int, max_size: int, filename: str, context: Optional[Dict[str, Any]] = None) -> ErrorResponse:
    """Error when uploaded file exceeds size limit"""
    file_size_mb = file_size / (1024 * 1024)
    max_size_mb = max_size / (1024 * 1024)

    return ErrorResponse(
        code=ErrorCode.VALIDATION_FILE_TOO_LARGE,
        message=f"File size {file_size_mb:.1f}MB exceeds maximum {max_size_mb:.1f}MB",
        user_message=f"File '{filename}' is too large ({file_size_mb:.1f}MB). Maximum file size is {max_size_mb:.1f}MB.",
        http_status=413,
        suggestion=f"Compress your image or reduce resolution to get under {max_size_mb:.1f}MB",
        retry=False,
        severity=ErrorSeverity.ERROR,
        context={**(context or {}), "file_size_bytes": file_size, "max_size_bytes": max_size, "filename": filename}
    )


def invalid_file_type_error(filename: str, file_type: str, allowed_types: list, context: Optional[Dict[str, Any]] = None) -> ErrorResponse:
    """Error when file type is not allowed"""
    return ErrorResponse(
        code=ErrorCode.VALIDATION_INVALID_TYPE,
        message=f"File type '{file_type}' not allowed",
        user_message=f"File '{filename}' has an unsupported format. Please upload JPG, PNG, or WebP images.",
        http_status=415,
        suggestion=f"Allowed types: {', '.join(allowed_types)}",
        retry=False,
        severity=ErrorSeverity.ERROR,
        context={**(context or {}), "filename": filename, "file_type": file_type, "allowed_types": allowed_types}
    )


def corrupt_image_error(filename: str, context: Optional[Dict[str, Any]] = None) -> ErrorResponse:
    """Error when image file is corrupt or unreadable"""
    return ErrorResponse(
        code=ErrorCode.VALIDATION_CORRUPT_IMAGE,
        message=f"Image file '{filename}' is corrupt or unreadable",
        user_message=f"Unable to read '{filename}'. The file may be corrupted. Please try re-exporting from your camera or photo editor.",
        http_status=422,
        suggestion="Try re-saving the image in a standard format (JPEG or PNG) and uploading again",
        retry=False,
        severity=ErrorSeverity.ERROR,
        context={**(context or {}), "filename": filename}
    )


def image_processing_error(filename: str, step: str, error_message: str, context: Optional[Dict[str, Any]] = None, stack_trace: Optional[str] = None) -> ErrorResponse:
    """Error during image processing"""
    return ErrorResponse(
        code=ErrorCode.PROCESSING_IMAGE_FAILED,
        message=f"Image processing failed at step '{step}': {error_message}",
        user_message=f"Failed to process '{filename}'. The image file may have an issue.",
        http_status=500,
        suggestion="Try uploading a different image or contact support if the issue persists",
        retry=False,
        severity=ErrorSeverity.ERROR,
        context={**(context or {}), "filename": filename, "step": step, "error": error_message},
        stack_trace=stack_trace
    )


def database_error(operation: str, error_message: str, context: Optional[Dict[str, Any]] = None, stack_trace: Optional[str] = None) -> ErrorResponse:
    """Database operation error"""
    return ErrorResponse(
        code=ErrorCode.DATABASE_CONNECTION_FAILED,
        message=f"Database operation '{operation}' failed: {error_message}",
        user_message="A database error occurred. Please try again or contact support if the issue persists.",
        http_status=500,
        suggestion="Check database connection, permissions, and disk space",
        retry=True,
        severity=ErrorSeverity.CRITICAL,
        context={**(context or {}), "operation": operation, "error": error_message},
        stack_trace=stack_trace
    )


def not_found_error(resource_type: str, resource_id: Any, context: Optional[Dict[str, Any]] = None) -> ErrorResponse:
    """Resource not found error"""
    return ErrorResponse(
        code=ErrorCode.DATABASE_NOT_FOUND,
        message=f"{resource_type} with ID '{resource_id}' not found",
        user_message=f"The requested {resource_type.lower()} could not be found.",
        http_status=404,
        suggestion=f"Verify the {resource_type.lower()} ID is correct",
        retry=False,
        severity=ErrorSeverity.ERROR,
        context={**(context or {}), "resource_type": resource_type, "resource_id": str(resource_id)}
    )


def claude_api_error(error_message: str, context: Optional[Dict[str, Any]] = None, stack_trace: Optional[str] = None) -> ErrorResponse:
    """Claude API general error"""
    return ErrorResponse(
        code=ErrorCode.EXTERNAL_CLAUDE_ERROR,
        message=f"Claude API error: {error_message}",
        user_message="AI caption generation failed. Your image will be uploaded with basic metadata.",
        http_status=502,
        suggestion="Check Claude API status and your API key configuration",
        docs_url="https://status.anthropic.com",
        retry=True,
        severity=ErrorSeverity.WARNING,
        context=context,
        stack_trace=stack_trace
    )


def internal_error(error_message: str, context: Optional[Dict[str, Any]] = None, stack_trace: Optional[str] = None) -> ErrorResponse:
    """Generic internal server error"""
    return ErrorResponse(
        code=ErrorCode.INTERNAL_ERROR,
        message=f"Internal error: {error_message}",
        user_message="An unexpected error occurred. Please try again or contact support.",
        http_status=500,
        suggestion="Check server logs for details",
        retry=True,
        severity=ErrorSeverity.ERROR,
        context=context,
        stack_trace=stack_trace
    )
