"""
Hensler Photography Backend API

Multi-tenant photography portfolio management system with:
- AI-powered image ingestion
- Click tracking and analytics
- Static site generation
- Admin interface
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import os

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
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
            "api": "/api"
        }
    }

# Admin dashboard
@app.get("/admin")
async def admin_dashboard(request: Request):
    """Admin dashboard UI"""
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {"request": request, "title": "Admin Dashboard"}
    )

# Admin upload page
@app.get("/admin/upload")
async def admin_upload(request: Request):
    """Admin upload interface"""
    return templates.TemplateResponse(
        "admin/upload.html",
        {"request": request, "title": "Upload Photos"}
    )

# Admin gallery management page
@app.get("/admin/gallery")
async def admin_gallery(request: Request):
    """Admin gallery management interface"""
    return templates.TemplateResponse(
        "admin/gallery.html",
        {"request": request, "title": "Manage Gallery"}
    )

# Include API routers
from api.routes.ingestion import router as ingestion_router
app.include_router(ingestion_router)

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
