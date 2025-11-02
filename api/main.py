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
import os
import time
import traceback
from pathlib import Path

# Import error handling and logging
from api.errors import ErrorResponse, internal_error
from api.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Hensler Photography API",
    description="Backend API for photography portfolio management",
    version="2.0.0"
)

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

        # Check if requesting an admin page (not the login page itself)
        path = str(request.url.path)
        is_admin_page = path.startswith("/admin") and path != "/admin/login"

        if is_browser and is_admin_page:
            logger.info(f"Redirecting unauthenticated browser request to login: {path}")
            return RedirectResponse(url="/admin/login", status_code=303)

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
    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request}
    )

# Import auth dependency
from api.routes.auth import get_current_user, User
from fastapi import Depends

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

    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "title": "Admin Dashboard",
            "current_user": current_user
        }
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

    return templates.TemplateResponse(
        "admin/upload.html",
        {
            "request": request,
            "title": "Upload Photos",
            "current_user": current_user
        }
    )

# Admin gallery management page (protected)
@app.get("/admin/gallery")
async def admin_gallery(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Admin gallery management interface (authenticated users only)"""
    # Check admin role
    if current_user.role != "admin":
        raise HTTPException(403, "Admin access required")

    return templates.TemplateResponse(
        "admin/gallery.html",
        {
            "request": request,
            "title": "Manage Gallery",
            "current_user": current_user
        }
    )

# Include API routers
from api.routes.ingestion import router as ingestion_router
from api.routes.auth import router as auth_router

app.include_router(ingestion_router)
app.include_router(auth_router)

# Track endpoint (public - for frontend JavaScript)
@app.post("/api/track")
async def track_event(event_type: str, image_id: int = None):
    """Track image events (views, clicks, etc.)"""
    # Placeholder - will implement with database
    return {
        "status": "ok",
        "tracked": {
            "event_type": event_type,
            "image_id": image_id
        }
    }

# Gallery API endpoint (public)
@app.get("/api/gallery/{username}")
async def get_gallery(username: str):
    """Get published images for a user"""
    # Placeholder - will fetch from database
    return {
        "username": username,
        "images": [],
        "count": 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
