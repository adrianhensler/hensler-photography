"""
Hensler Photography Backend API

Multi-tenant photography portfolio management system with:
- AI-powered image ingestion
- Click tracking and analytics
- Static site generation
- Admin interface
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import os
import time
import traceback
from pathlib import Path

# Import error handling and logging
from api.errors import ErrorResponse, internal_error
from api.logging_config import get_logger
from api.rate_limit import limiter
from api.csrf import add_csrf_token_to_context
from api.models import TrackingEvent

# Initialize logger
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Hensler Photography API",
    description="Backend API for photography portfolio management",
    version="2.0.0"
)

# Add rate limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware for frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://adrian.hensler.photography:8080",
        "https://liam.hensler.photography:8080",
        "https://hensler.photography:8080",
        "https://hensler.photography:4100",
        "http://localhost:8080",
        "http://localhost:4100",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handlers

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle FastAPI HTTP exceptions with structured error response"""
    from fastapi.responses import RedirectResponse

    # Log the error
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={
            "context": {
                "path": str(request.url.path),
                "method": request.method,
                "status_code": exc.status_code
            }
        }
    )

    # Special handling: Redirect browser requests to login page on 401
    if exc.status_code == 401:
        # Check if this is a browser request (looking for HTML)
        accept = request.headers.get("accept", "")
        is_browser = "text/html" in accept

        # Check if requesting a protected page (not the login page itself)
        path = str(request.url.path)
        is_protected_page = (path.startswith("/admin") or path.startswith("/manage")) and path not in ["/admin/login", "/manage/login"]

        if is_browser and is_protected_page:
            logger.info(f"Redirecting unauthenticated browser request to login: {path}")
            return RedirectResponse(url="/manage/login", status_code=303)

    # Return structured error response for API calls
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "user_message": exc.detail,
                "details": {
                    "severity": "error",
                    "retry": False
                }
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unhandled exceptions"""
    # Get stack trace
    stack_trace = traceback.format_exc()

    # Log the error with full context
    logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=exc,
        extra={
            "context": {
                "path": str(request.url.path),
                "method": request.method,
                "exception_type": type(exc).__name__
            }
        }
    )

    # Create structured error response
    error = internal_error(
        error_message=str(exc),
        context={
            "path": str(request.url.path),
            "method": request.method,
            "exception_type": type(exc).__name__
        },
        stack_trace=stack_trace
    )

    return JSONResponse(
        status_code=error.http_status,
        content=error.to_dict()
    )


# Mount static files and templates
app.mount("/static", StaticFiles(directory="api/static"), name="static")
app.mount("/assets/gallery", StaticFiles(directory="/app/assets/gallery"), name="gallery")
templates = Jinja2Templates(directory="api/templates")

# Health check endpoint
@app.get("/healthz")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "ok", "service": "api"}

# Root endpoint
@app.get("/")
async def root():
    """API root - shows basic info"""
    return {
        "service": "Hensler Photography API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "docs": "/docs",
            "admin": "/admin",
            "api": "/api",
            "health": "/api/health"
        }
    }


# Detailed health check endpoint
@app.get("/api/health")
async def health_check_detailed():
    """
    Comprehensive health check for system diagnostics.

    Checks:
    - Database connectivity
    - Claude API configuration
    - Storage availability
    - Service status

    Useful for both human admins and AI assistants to diagnose issues.
    """
    from api.database import DATABASE_PATH
    import aiosqlite
    import shutil

    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "services": {},
        "warnings": [],
        "errors": []
    }

    # Check database
    try:
        start = time.time()
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("SELECT 1")
            latency = (time.time() - start) * 1000
            health_status["services"]["database"] = {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "path": str(DATABASE_PATH)
            }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["services"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["errors"].append(f"Database connection failed: {str(e)}")

    # Check Claude API configuration
    claude_api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not claude_api_key:
        health_status["status"] = "degraded"
        health_status["services"]["claude_api"] = {
            "status": "unavailable",
            "error": "API key not configured"
        }
        health_status["warnings"].append("ANTHROPIC_API_KEY not set - AI features disabled")
    else:
        health_status["services"]["claude_api"] = {
            "status": "configured",
            "note": "API key is set (not tested)"
        }

    # Check storage
    try:
        gallery_path = Path("/app/assets/gallery")
        gallery_path.mkdir(parents=True, exist_ok=True)

        # Get disk space
        stat = shutil.disk_usage("/app/assets")
        free_gb = stat.free / (1024**3)
        total_gb = stat.total / (1024**3)
        used_percent = ((stat.total - stat.free) / stat.total) * 100

        storage_status = "healthy"
        if free_gb < 1.0:
            storage_status = "critical"
            health_status["status"] = "degraded"
            health_status["errors"].append(f"Storage critically low: {free_gb:.1f}GB remaining")
        elif free_gb < 5.0:
            storage_status = "warning"
            health_status["warnings"].append(f"Storage running low: {free_gb:.1f}GB remaining")

        health_status["services"]["storage"] = {
            "status": storage_status,
            "free_gb": round(free_gb, 2),
            "total_gb": round(total_gb, 2),
            "used_percent": round(used_percent, 1),
            "gallery_path": str(gallery_path)
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["services"]["storage"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["errors"].append(f"Storage check failed: {str(e)}")

    # Overall status summary
    health_status["summary"] = {
        "total_services": len(health_status["services"]),
        "healthy_services": sum(1 for s in health_status["services"].values() if s.get("status") in ["healthy", "configured"]),
        "total_warnings": len(health_status["warnings"]),
        "total_errors": len(health_status["errors"])
    }

    return health_status


# Login page (public)
@app.get("/admin/login")
async def admin_login(request: Request):
    """Admin login page"""
    context = {"request": request}
    context = add_csrf_token_to_context(request, context)
    return templates.TemplateResponse(
        "admin/login.html",
        context
    )

@app.get("/manage/login")
async def manage_login(request: Request):
    """Photographer login page (same as admin login)"""
    context = {"request": request}
    context = add_csrf_token_to_context(request, context)
    return templates.TemplateResponse(
        "admin/login.html",
        context
    )

# Import auth dependencies
from api.routes.auth import get_current_user, get_current_user_for_subdomain, User
from fastapi import Depends

# Photographer dashboard (protected - subdomain validated)
@app.get("/manage")
async def photographer_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user_for_subdomain)
):
    """Photographer dashboard (authenticated users)"""
    context = {
        "request": request,
        "title": "Dashboard",
        "current_user": current_user
    }
    context = add_csrf_token_to_context(request, context)
    return templates.TemplateResponse(
        "photographer/dashboard.html",
        context
    )

# Photographer upload page (protected)
@app.get("/manage/upload")
async def photographer_upload(
    request: Request,
    current_user: User = Depends(get_current_user_for_subdomain)
):
    """Photographer upload interface (authenticated users)"""
    context = {
        "request": request,
        "title": "Upload Photos",
        "current_user": current_user
    }
    context = add_csrf_token_to_context(request, context)
    return templates.TemplateResponse(
        "photographer/upload.html",
        context
    )

# Photographer gallery management page (protected)
@app.get("/manage/gallery")
async def photographer_gallery(
    request: Request,
    current_user: User = Depends(get_current_user_for_subdomain)
):
    """Photographer gallery management interface (authenticated users)"""
    context = {
        "request": request,
        "title": "My Gallery",
        "current_user": current_user
    }
    context = add_csrf_token_to_context(request, context)
    return templates.TemplateResponse(
        "photographer/gallery.html",
        context
    )

# Photographer analytics page (protected)
@app.get("/manage/analytics")
async def photographer_analytics(
    request: Request,
    current_user: User = Depends(get_current_user_for_subdomain)
):
    """Photographer analytics dashboard (authenticated users)"""
    context = {
        "request": request,
        "title": "Portfolio Analytics",
        "current_user": current_user
    }
    context = add_csrf_token_to_context(request, context)
    return templates.TemplateResponse(
        "photographer/analytics.html",
        context
    )

# Photographer settings page (protected)
@app.get("/manage/settings")
async def photographer_settings(
    request: Request,
    current_user: User = Depends(get_current_user_for_subdomain)
):
    """Photographer account settings (authenticated users)"""
    context = {
        "request": request,
        "title": "Settings",
        "current_user": current_user
    }
    context = add_csrf_token_to_context(request, context)
    return templates.TemplateResponse(
        "photographer/settings.html",
        context
    )

# Admin dashboard (protected)
@app.get("/admin")
async def admin_dashboard(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Admin dashboard UI (authenticated users only)"""
    # Check admin role
    if current_user.role != "admin":
        raise HTTPException(403, "Admin access required")

    context = {
        "request": request,
        "title": "Admin Dashboard",
        "current_user": current_user
    }
    context = add_csrf_token_to_context(request, context)
    return templates.TemplateResponse(
        "admin/dashboard.html",
        context
    )

# Admin upload page (protected)
@app.get("/admin/upload")
async def admin_upload(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Admin upload interface (authenticated users only)"""
    # Check admin role
    if current_user.role != "admin":
        raise HTTPException(403, "Admin access required")

    context = {
        "request": request,
        "title": "Upload Photos",
        "current_user": current_user
    }
    context = add_csrf_token_to_context(request, context)
    return templates.TemplateResponse(
        "admin/upload.html",
        context
    )

# Admin gallery removed - photographers use /manage/gallery instead

# Include API routers
from api.routes.ingestion import router as ingestion_router
from api.routes.auth import router as auth_router
from api.routes.gallery import router as gallery_router
from api.routes.photographer import router as photographer_router
from api.routes.analytics import router as analytics_router

app.include_router(ingestion_router)
app.include_router(auth_router)
app.include_router(gallery_router)
app.include_router(photographer_router)
app.include_router(analytics_router)

# Track endpoint (public - for frontend JavaScript)
@app.post("/api/track")
@limiter.limit("100/minute")  # Generous rate limit for analytics
async def track_event(request: Request, event: TrackingEvent):
    """
    Track image engagement events (views, clicks, lightbox opens)

    Privacy-preserving analytics:
    - IP addresses are hashed (SHA256 + salt)
    - No cookies or persistent identifiers
    - Session IDs are client-generated and ephemeral
    """
    from api.database import get_db_connection
    import hashlib
    import os

    # Get client IP and hash it for privacy
    client_ip = request.client.host if request.client else None
    ip_hash = None
    if client_ip:
        # Use JWT secret as salt for IP hashing
        salt = os.getenv("JWT_SECRET_KEY", "INSECURE_DEV_KEY")
        ip_hash = hashlib.sha256(f"{client_ip}{salt}".encode()).hexdigest()[:16]

    # Get user agent and referrer from headers
    user_agent = request.headers.get("user-agent")
    referrer = event.referrer or request.headers.get("referer")

    # Store event in database
    try:
        async with get_db_connection() as db:
            cursor = await db.execute("""
                INSERT INTO image_events
                (image_id, event_type, user_agent, referrer, ip_hash, session_id, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                event.image_id,
                event.event_type,
                user_agent,
                referrer,
                ip_hash,
                event.session_id,
                event.metadata
            ))
            await db.commit()
            event_id = cursor.lastrowid

            logger.info(
                f"Tracked event: {event.event_type}",
                extra={
                    "context": {
                        "event_id": event_id,
                        "event_type": event.event_type,
                        "image_id": event.image_id,
                        "session_id": event.session_id
                    }
                }
            )

            return {
                "success": True,
                "event_id": event_id
            }
    except Exception as e:
        logger.error(f"Failed to track event: {str(e)}", exc_info=e)
        # Don't fail the request - analytics shouldn't break user experience
        return {
            "success": False,
            "error": "Failed to track event"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
