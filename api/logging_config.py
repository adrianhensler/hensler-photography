"""
Structured JSON Logging Configuration

Provides machine-readable logs for both human debugging and AI diagnosis.
"""

import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add extra fields from LogRecord
        if hasattr(record, "context"):
            log_data["context"] = record.context

        if hasattr(record, "error_code"):
            log_data["error_code"] = record.error_code

        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        if hasattr(record, "image_id"):
            log_data["image_id"] = record.image_id

        if hasattr(record, "filename"):
            log_data["filename"] = record.filename

        return json.dumps(log_data)


class ContextLogger(logging.LoggerAdapter):
    """Logger adapter that adds context to all log messages"""

    def __init__(self, logger: logging.Logger, context: Dict[str, Any] = None):
        super().__init__(logger, context or {})

    def process(self, msg, kwargs):
        """Add context to log record"""
        extra = kwargs.get("extra", {})
        extra.update(self.extra)
        kwargs["extra"] = extra
        return msg, kwargs


def setup_logging(
    log_level: str = "INFO", log_file: Path = None, json_format: bool = True
) -> logging.Logger:
    """
    Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        json_format: Use JSON format (True) or human-readable (False)

    Returns:
        Configured logger instance
    """
    # Create root logger
    logger = logging.getLogger("hensler_photography")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        # Human-readable format for local development
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
        )

    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str, context: Dict[str, Any] = None) -> ContextLogger:
    """
    Get a logger with optional context.

    Args:
        name: Logger name (usually __name__)
        context: Optional context dict to add to all log messages

    Returns:
        ContextLogger instance
    """
    base_logger = logging.getLogger(f"hensler_photography.{name}")
    return ContextLogger(base_logger, context)


# Convenience functions for logging with context


def log_error(
    logger: logging.Logger,
    message: str,
    error: Exception = None,
    error_code: str = None,
    context: Dict[str, Any] = None,
):
    """
    Log an error with structured context.

    Args:
        logger: Logger instance
        message: Error message
        error: Optional exception object
        error_code: Optional error code (from ErrorCode enum)
        context: Optional context dictionary
    """
    extra = {"context": context or {}}
    if error_code:
        extra["error_code"] = error_code

    logger.error(message, exc_info=error, extra=extra)


def log_warning(
    logger: logging.Logger, message: str, error_code: str = None, context: Dict[str, Any] = None
):
    """
    Log a warning with structured context.

    Args:
        logger: Logger instance
        message: Warning message
        error_code: Optional error code
        context: Optional context dictionary
    """
    extra = {"context": context or {}}
    if error_code:
        extra["error_code"] = error_code

    logger.warning(message, extra=extra)


def log_info(logger: logging.Logger, message: str, context: Dict[str, Any] = None):
    """
    Log info with structured context.

    Args:
        logger: Logger instance
        message: Info message
        context: Optional context dictionary
    """
    logger.info(message, extra={"context": context or {}})


# Initialize logging on import
_root_logger = setup_logging(
    log_level="INFO", json_format=True  # Always use JSON in production for AI readability
)
