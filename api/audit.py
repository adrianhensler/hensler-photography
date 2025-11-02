"""
Audit logging for Hensler Photography API

Provides comprehensive audit trail for all security-critical operations.
"""

from fastapi import Request
from typing import Optional, Any
import json
from datetime import datetime

from api.database import get_db_connection
from api.logging_config import get_logger

logger = get_logger(__name__)


def get_client_ip(request: Request) -> Optional[str]:
    """
    Extract client IP address from request, handling proxies.

    Args:
        request: FastAPI request object

    Returns:
        IP address string or None
    """
    # Check X-Forwarded-For header (set by proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first (original client)
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header (set by some proxies)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct connection IP
    if request.client:
        return request.client.host

    return None


def get_user_agent(request: Request) -> Optional[str]:
    """
    Extract user agent string from request.

    Args:
        request: FastAPI request object

    Returns:
        User agent string or None
    """
    return request.headers.get("User-Agent")


async def log_audit_event(
    user_id: int,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
    request: Optional[Request] = None
) -> int:
    """
    Log an audit event to the database.

    Args:
        user_id: ID of user performing the action
        action: Action performed (e.g., "user.login", "image.delete")
        resource_type: Type of resource affected (e.g., "user", "image")
        resource_id: ID of resource affected
        old_value: Previous state of resource (for updates/deletes)
        new_value: New state of resource (for creates/updates)
        request: Optional FastAPI request object for IP/user agent

    Returns:
        Audit log entry ID
    """
    try:
        # Extract request metadata if provided
        ip_address = None
        user_agent = None
        if request:
            ip_address = get_client_ip(request)
            user_agent = get_user_agent(request)

        # Serialize values to JSON if they're complex objects
        old_value_str = None
        new_value_str = None

        if old_value is not None:
            if isinstance(old_value, (dict, list)):
                old_value_str = json.dumps(old_value, default=str)
            else:
                old_value_str = str(old_value)

        if new_value is not None:
            if isinstance(new_value, (dict, list)):
                new_value_str = json.dumps(new_value, default=str)
            else:
                new_value_str = str(new_value)

        # Insert into audit_log table
        async with get_db_connection() as db:
            cursor = await db.execute(
                """
                INSERT INTO audit_log (
                    user_id, action, resource_type, resource_id,
                    old_value, new_value, ip_address, user_agent, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    action,
                    resource_type,
                    resource_id,
                    old_value_str,
                    new_value_str,
                    ip_address,
                    user_agent,
                    datetime.utcnow()
                )
            )
            await db.commit()
            audit_id = cursor.lastrowid

        logger.info(
            f"Audit log entry created: {action}",
            extra={
                "context": {
                    "audit_id": audit_id,
                    "user_id": user_id,
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "ip_address": ip_address
                }
            }
        )

        return audit_id

    except Exception as e:
        logger.error(
            f"Failed to log audit event: {e}",
            exc_info=e,
            extra={
                "context": {
                    "user_id": user_id,
                    "action": action,
                    "resource_type": resource_type,
                    "resource_id": resource_id
                }
            }
        )
        # Don't fail the main operation if audit logging fails
        return -1


# Convenience functions for common audit events

async def audit_login(user_id: int, username: str, request: Request) -> int:
    """Log successful user login"""
    return await log_audit_event(
        user_id=user_id,
        action="auth.login",
        resource_type="user",
        resource_id=user_id,
        new_value={"username": username, "timestamp": datetime.utcnow().isoformat()},
        request=request
    )


async def audit_logout(user_id: int, username: str, request: Request) -> int:
    """Log user logout"""
    return await log_audit_event(
        user_id=user_id,
        action="auth.logout",
        resource_type="user",
        resource_id=user_id,
        new_value={"username": username, "timestamp": datetime.utcnow().isoformat()},
        request=request
    )


async def audit_password_change(user_id: int, username: str, request: Request) -> int:
    """Log password change"""
    return await log_audit_event(
        user_id=user_id,
        action="auth.password_change",
        resource_type="user",
        resource_id=user_id,
        new_value={"username": username, "timestamp": datetime.utcnow().isoformat()},
        request=request
    )


async def audit_user_create(
    admin_user_id: int,
    new_user_id: int,
    new_username: str,
    new_user_role: str,
    request: Request
) -> int:
    """Log new user creation"""
    return await log_audit_event(
        user_id=admin_user_id,
        action="user.create",
        resource_type="user",
        resource_id=new_user_id,
        new_value={
            "username": new_username,
            "role": new_user_role,
            "created_by": admin_user_id
        },
        request=request
    )


async def audit_image_upload(user_id: int, image_id: int, filename: str, request: Request) -> int:
    """Log image upload"""
    return await log_audit_event(
        user_id=user_id,
        action="image.upload",
        resource_type="image",
        resource_id=image_id,
        new_value={"filename": filename, "image_id": image_id},
        request=request
    )


async def audit_image_delete(
    user_id: int,
    image_id: int,
    image_data: dict,
    request: Request
) -> int:
    """Log image deletion"""
    return await log_audit_event(
        user_id=user_id,
        action="image.delete",
        resource_type="image",
        resource_id=image_id,
        old_value=image_data,
        request=request
    )


async def audit_image_publish(user_id: int, image_id: int, published: bool, request: Request) -> int:
    """Log image publish/unpublish"""
    action = "image.publish" if published else "image.unpublish"
    return await log_audit_event(
        user_id=user_id,
        action=action,
        resource_type="image",
        resource_id=image_id,
        new_value={"published": published},
        request=request
    )


async def audit_image_update(
    user_id: int,
    image_id: int,
    old_metadata: dict,
    new_metadata: dict,
    request: Request
) -> int:
    """Log image metadata update"""
    return await log_audit_event(
        user_id=user_id,
        action="image.update",
        resource_type="image",
        resource_id=image_id,
        old_value=old_metadata,
        new_value=new_metadata,
        request=request
    )


async def get_audit_logs(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0
) -> list:
    """
    Query audit logs with filters.

    Args:
        user_id: Filter by user ID
        action: Filter by action type
        resource_type: Filter by resource type
        resource_id: Filter by resource ID
        limit: Maximum results to return
        offset: Pagination offset

    Returns:
        List of audit log entries
    """
    query = """
        SELECT id, user_id, action, resource_type, resource_id,
               old_value, new_value, ip_address, user_agent, timestamp
        FROM audit_log
        WHERE 1=1
    """
    params = []

    if user_id is not None:
        query += " AND user_id = ?"
        params.append(user_id)

    if action:
        query += " AND action = ?"
        params.append(action)

    if resource_type:
        query += " AND resource_type = ?"
        params.append(resource_type)

    if resource_id is not None:
        query += " AND resource_id = ?"
        params.append(resource_id)

    query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    async with get_db_connection() as db:
        cursor = await db.execute(query, tuple(params))
        rows = await cursor.fetchall()

    logs = []
    for row in rows:
        logs.append({
            "id": row[0],
            "user_id": row[1],
            "action": row[2],
            "resource_type": row[3],
            "resource_id": row[4],
            "old_value": row[5],
            "new_value": row[6],
            "ip_address": row[7],
            "user_agent": row[8],
            "timestamp": row[9]
        })

    return logs
