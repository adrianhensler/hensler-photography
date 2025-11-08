"""
Pydantic models for input validation and serialization

Provides type-safe data validation for all API inputs.
"""

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Literal
from datetime import datetime
import re


# ============================================================================
# User Models
# ============================================================================

class UserCreate(BaseModel):
    """Model for creating a new user (admin only)"""
    username: str = Field(
        min_length=3,
        max_length=50,
        description="Username (3-50 characters, alphanumeric, underscore, hyphen only)"
    )
    email: EmailStr = Field(description="Valid email address")
    display_name: str = Field(
        min_length=1,
        max_length=100,
        description="Display name for UI"
    )
    password: str = Field(
        min_length=12,
        description="Password (validated separately for complexity)"
    )
    role: Literal["admin", "photographer"] = Field(
        default="photographer",
        description="User role"
    )

    @validator('username')
    def validate_username(cls, v):
        # Only allow alphanumeric, underscore, hyphen
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError(
                'Username can only contain letters, numbers, underscores, and hyphens'
            )

        # Check reserved usernames
        reserved = {'admin', 'root', 'system', 'api', 'www', 'mail', 'ftp', 'smtp'}
        if v.lower() in reserved:
            raise ValueError(f'Username "{v}" is reserved and cannot be used')

        return v

    @validator('display_name')
    def validate_display_name(cls, v):
        # Prevent excessive whitespace
        if '  ' in v:
            raise ValueError('Display name cannot contain multiple consecutive spaces')

        # Trim whitespace
        v = v.strip()

        if not v:
            raise ValueError('Display name cannot be empty or only whitespace')

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "username": "photographer1",
                "email": "photo@example.com",
                "display_name": "Professional Photographer",
                "password": "SecurePass123!",
                "role": "photographer"
            }
        }


class UserLogin(BaseModel):
    """Model for user login"""
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class PasswordChange(BaseModel):
    """Model for changing password"""
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=12)
    confirm_password: str = Field(min_length=12)

    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class UserResponse(BaseModel):
    """Model for user data in responses"""
    id: int
    username: str
    display_name: str
    email: str
    role: str

    class Config:
        from_attributes = True


# ============================================================================
# Image Models
# ============================================================================

class ImageMetadataUpdate(BaseModel):
    """Model for updating image metadata"""
    title: Optional[str] = Field(
        None,
        max_length=200,
        description="Image title"
    )
    caption: Optional[str] = Field(
        None,
        max_length=1000,
        description="Image caption/description"
    )
    description: Optional[str] = Field(
        None,
        max_length=2000,
        description="Detailed description"
    )
    tags: Optional[str] = Field(
        None,
        max_length=500,
        description="Comma-separated tags"
    )
    category: Optional[str] = Field(
        None,
        max_length=100,
        description="Image category"
    )
    location: Optional[str] = Field(
        None,
        max_length=200,
        description="Location where photo was taken"
    )

    # Technical metadata (editable for manual correction)
    camera: Optional[str] = Field(
        None,
        max_length=200,
        description="Camera body (e.g., 'Canon EOS R5')"
    )
    lens: Optional[str] = Field(
        None,
        max_length=200,
        description="Lens used (e.g., 'RF 24-70mm f/2.8')"
    )
    focal_length: Optional[str] = Field(
        None,
        max_length=50,
        description="Focal length (e.g., '50mm')"
    )
    aperture: Optional[str] = Field(
        None,
        max_length=50,
        description="Aperture (e.g., 'f/2.8')"
    )
    shutter_speed: Optional[str] = Field(
        None,
        max_length=50,
        description="Shutter speed (e.g., '1/250s')"
    )
    iso: Optional[str] = Field(
        None,
        max_length=50,
        description="ISO value (e.g., '400')"
    )
    date_taken: Optional[str] = Field(
        None,
        max_length=100,
        description="Date/time photo was taken (editable for timezone correction)"
    )

    @validator('title', 'caption', 'description', 'category', 'location', 'camera', 'lens')
    def strip_whitespace(cls, v):
        if v is not None:
            v = v.strip()
            if not v:  # If empty after stripping, return None
                return None
        return v

    @validator('iso')
    def validate_iso(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                return None

            # ISO should be numeric (allow just digits)
            if not re.match(r'^\d+$', v):
                raise ValueError('ISO must be a number (e.g., 100, 400, 3200)')

            # Validate reasonable ISO range (25 to 10,000,000 for modern cameras)
            iso_int = int(v)
            if iso_int < 25 or iso_int > 10000000:
                raise ValueError('ISO must be between 25 and 10,000,000')

        return v

    @validator('aperture')
    def validate_aperture(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                return None

            # Aperture should match f/N.N or f/N format
            if not re.match(r'^f/\d+(\.\d+)?$', v, re.IGNORECASE):
                raise ValueError('Aperture must be in format f/2.8 or f/1.4')

        return v

    @validator('shutter_speed')
    def validate_shutter_speed(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                return None

            # Allow formats: 1/250s, 1/1000, 1", 30", 2.5s, etc.
            valid_patterns = [
                r'^\d+/\d+s?$',      # 1/250s or 1/250
                r'^\d+(\.\d+)?"$',   # 1" or 2.5"
                r'^\d+(\.\d+)?s$',   # 1s or 2.5s
            ]

            if not any(re.match(pattern, v) for pattern in valid_patterns):
                raise ValueError('Shutter speed must be in format 1/250s, 1/1000, 1", or 2.5s')

        return v

    @validator('focal_length')
    def validate_focal_length(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                return None

            # Allow formats: 50mm, 24-70mm, 100-400mm
            if not re.match(r'^\d+(-\d+)?mm$', v, re.IGNORECASE):
                raise ValueError('Focal length must be in format 50mm or 24-70mm')

        return v

    @validator('date_taken')
    def validate_date_taken(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                return None

            # Try to parse common date formats
            from datetime import datetime
            valid_formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d %H:%M',
                '%Y-%m-%d',
                '%Y/%m/%d %H:%M:%S',
                '%Y/%m/%d %H:%M',
                '%Y/%m/%d',
            ]

            parsed = False
            for fmt in valid_formats:
                try:
                    datetime.strptime(v, fmt)
                    parsed = True
                    break
                except ValueError:
                    continue

            if not parsed:
                raise ValueError('Date must be in format YYYY-MM-DD HH:MM:SS or YYYY-MM-DD')

        return v

    @validator('tags')
    def validate_tags(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                return None

            # Normalize tags: remove extra spaces, ensure proper comma separation
            tags = [tag.strip() for tag in v.split(',')]
            tags = [tag for tag in tags if tag]  # Remove empty tags

            if len(tags) > 50:
                raise ValueError('Maximum 50 tags allowed')

            # Check individual tag length
            for tag in tags:
                if len(tag) > 50:
                    raise ValueError(f'Tag "{tag}" is too long (max 50 characters)')

            return ', '.join(tags)

        return v

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Sunset at Peggy's Cove",
                "caption": "Golden hour at the famous lighthouse",
                "tags": "sunset, lighthouse, nova scotia, landscape",
                "category": "Landscape"
            }
        }


class ImageUpload(BaseModel):
    """Model for image upload metadata (from AI analysis)"""
    title: Optional[str] = Field(None, max_length=200)
    caption: Optional[str] = Field(None, max_length=1000)
    description: Optional[str] = Field(None, max_length=2000)
    tags: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=100)

    # EXIF data
    camera_make: Optional[str] = Field(None, max_length=100)
    camera_model: Optional[str] = Field(None, max_length=100)
    lens: Optional[str] = Field(None, max_length=200)
    focal_length: Optional[str] = Field(None, max_length=50)
    aperture: Optional[str] = Field(None, max_length=50)
    shutter_speed: Optional[str] = Field(None, max_length=50)
    iso: Optional[int] = Field(None, ge=1, le=10000000)
    location: Optional[str] = Field(None, max_length=200)


class ImageResponse(BaseModel):
    """Model for image data in responses"""
    id: int
    user_id: int
    filename: str
    slug: str
    title: Optional[str]
    caption: Optional[str]
    category: Optional[str]
    tags: Optional[str]
    published: bool
    featured: bool
    width: Optional[int]
    height: Optional[int]
    created_at: datetime

    # Computed fields
    thumbnail_url: str

    class Config:
        from_attributes = True


# ============================================================================
# Audit Log Models
# ============================================================================

class AuditLogEntry(BaseModel):
    """Model for audit log entries"""
    user_id: int
    action: str = Field(
        max_length=100,
        description="Action performed (e.g., 'image.delete', 'user.create')"
    )
    resource_type: Optional[str] = Field(None, max_length=50)
    resource_id: Optional[int] = None
    old_value: Optional[str] = Field(None, max_length=10000)
    new_value: Optional[str] = Field(None, max_length=10000)
    ip_address: Optional[str] = Field(None, max_length=50)
    user_agent: Optional[str] = Field(None, max_length=500)


# ============================================================================
# Common Models
# ============================================================================

class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = True
    message: str


class ErrorResponse(BaseModel):
    """Standard error response"""
    success: bool = False
    error: dict


# ============================================================================
# Analytics Models
# ============================================================================

class TrackingEvent(BaseModel):
    """Model for tracking image engagement events"""
    event_type: Literal["gallery_click", "lightbox_open", "page_view"] = Field(
        description="Type of event being tracked"
    )
    image_id: Optional[int] = Field(
        None,
        description="Image ID (optional for page_view events)"
    )
    session_id: Optional[str] = Field(
        None,
        max_length=100,
        description="Client-generated session ID for grouping events"
    )
    referrer: Optional[str] = Field(
        None,
        max_length=500,
        description="HTTP referrer"
    )

    @validator('image_id')
    def validate_image_id_for_type(cls, v, values):
        """Require image_id for gallery_click and lightbox_open"""
        event_type = values.get('event_type')
        if event_type in ['gallery_click', 'lightbox_open'] and v is None:
            raise ValueError(f'{event_type} events require an image_id')
        return v
