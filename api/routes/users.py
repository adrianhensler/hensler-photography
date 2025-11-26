"""
User profile management routes
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional

from api.routes.auth import get_current_user, User
from api.database import get_db_connection
from api.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/users", tags=["users"])


class UserUpdate(BaseModel):
    """Model for updating user profile"""
    display_name: Optional[str] = Field(None, max_length=200)
    bio: Optional[str] = Field(None, max_length=1000)
    ai_style: Optional[str] = Field(None, pattern="^(technical|artistic|documentary|balanced)$")


@router.get("/me")
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile"""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "display_name": current_user.display_name,
        "role": current_user.role,
        "subdomain": current_user.subdomain,
        "bio": current_user.bio,
        "ai_style": current_user.ai_style,
    }


@router.patch("/me")
async def update_current_user_profile(
    updates: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update current user's profile"""
    # Convert to dict, exclude None values
    update_dict = updates.dict(exclude_none=True)

    if not update_dict:
        raise HTTPException(400, "No valid fields to update")

    async with get_db_connection() as db:
        # Build dynamic update query
        fields = []
        values = []

        for field, value in update_dict.items():
            fields.append(f"{field} = ?")
            values.append(value)

        values.append(current_user.id)

        query = f"UPDATE users SET {', '.join(fields)} WHERE id = ?"
        await db.execute(query, tuple(values))
        await db.commit()

    logger.info(
        f"User profile updated: {current_user.username}",
        extra={"context": {"user_id": current_user.id, "updated_fields": list(update_dict.keys())}}
    )

    return {
        "success": True,
        "updated_fields": list(update_dict.keys())
    }
