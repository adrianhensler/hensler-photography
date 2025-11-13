"""
Analytics routes for Hensler Photography API

Provides engagement metrics for photographers to track image performance.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from api.routes.auth import get_current_user_for_subdomain, User
from api.database import get_db_connection
from api.logging_config import get_logger
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import aiosqlite

# Initialize logger
logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/analytics", tags=["analytics"])


async def _verify_user_access(current_user: User, user_id: int):
    """Verify user can access analytics for given user_id"""
    if current_user.role == "admin":
        return  # Admins can see all analytics

    if current_user.id != user_id:
        raise HTTPException(403, "Not authorized to view these analytics")


@router.get("/overview")
async def get_analytics_overview(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    current_user: User = Depends(get_current_user_for_subdomain)
):
    """
    Get analytics overview for photographer dashboard.

    Returns aggregate metrics:
    - Total views (page_view events)
    - Unique visitors (distinct sessions)
    - Gallery clicks (gallery_click events)
    - Lightbox opens (lightbox_open events)
    - Click-through rate
    - Trends (comparison to previous period)
    """
    user_id = current_user.id
    since = datetime.now() - timedelta(days=days)
    prev_since = since - timedelta(days=days)  # Previous period for comparison

    try:
        async with get_db_connection() as db:
            # Current period metrics
            cursor = await db.execute("""
                SELECT
                    COUNT(CASE WHEN e.event_type = 'page_view' THEN 1 END) as views,
                    COUNT(DISTINCT e.session_id) as visitors,
                    COUNT(CASE WHEN e.event_type = 'gallery_click' THEN 1 END) as clicks,
                    COUNT(CASE WHEN e.event_type = 'lightbox_open' THEN 1 END) as lightbox_opens
                FROM image_events e
                LEFT JOIN images i ON e.image_id = i.id
                WHERE (i.user_id = ? OR e.image_id IS NULL)
                AND e.timestamp >= ?
            """, (user_id, since))

            current = await cursor.fetchone()

            # Previous period metrics for trend calculation
            cursor = await db.execute("""
                SELECT
                    COUNT(CASE WHEN e.event_type = 'page_view' THEN 1 END) as views,
                    COUNT(DISTINCT e.session_id) as visitors,
                    COUNT(CASE WHEN e.event_type = 'gallery_click' THEN 1 END) as clicks,
                    COUNT(CASE WHEN e.event_type = 'lightbox_open' THEN 1 END) as lightbox_opens
                FROM image_events e
                LEFT JOIN images i ON e.image_id = i.id
                WHERE (i.user_id = ? OR e.image_id IS NULL)
                AND e.timestamp >= ? AND e.timestamp < ?
            """, (user_id, prev_since, since))

            previous = await cursor.fetchone()

            # Calculate metrics
            views = current[0] or 0
            visitors = current[1] or 0
            clicks = current[2] or 0
            lightbox_opens = current[3] or 0

            prev_views = previous[0] or 0
            prev_visitors = previous[1] or 0
            prev_clicks = previous[2] or 0

            # Calculate click-through rate
            click_rate = (clicks / views) if views > 0 else 0

            # Calculate trends (percentage change)
            def calc_trend(current, previous):
                if previous == 0:
                    return 0 if current == 0 else 100
                return round(((current - previous) / previous) * 100, 1)

            views_trend = calc_trend(views, prev_views)
            visitors_trend = calc_trend(visitors, prev_visitors)
            clicks_trend = calc_trend(clicks, prev_clicks)

            logger.info(
                f"Analytics overview generated for user {user_id}",
                extra={
                    "context": {
                        "user_id": user_id,
                        "days": days,
                        "views": views,
                        "visitors": visitors
                    }
                }
            )

            return {
                "views": views,
                "views_trend": views_trend,
                "visitors": visitors,
                "visitors_trend": visitors_trend,
                "clicks": clicks,
                "clicks_trend": clicks_trend,
                "lightbox_opens": lightbox_opens,
                "click_rate": round(click_rate, 3),
                "period_days": days
            }

    except Exception as e:
        logger.error(f"Failed to get analytics overview: {str(e)}", exc_info=e)
        raise HTTPException(500, "Failed to retrieve analytics data")


@router.get("/timeline")
async def get_analytics_timeline(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    metric: str = Query("views", regex="^(views|clicks|lightbox_opens)$", description="Metric to chart"),
    current_user: User = Depends(get_current_user_for_subdomain)
):
    """
    Get time-series analytics data for charts.

    Returns daily counts for specified metric (views, clicks, or lightbox_opens).
    """
    user_id = current_user.id
    since = datetime.now() - timedelta(days=days)

    # Map metric to event type
    event_type_map = {
        "views": "page_view",
        "clicks": "gallery_click",
        "lightbox_opens": "lightbox_open"
    }
    event_type = event_type_map[metric]

    try:
        async with get_db_connection() as db:
            cursor = await db.execute("""
                SELECT
                    DATE(e.timestamp) as date,
                    COUNT(*) as count
                FROM image_events e
                LEFT JOIN images i ON e.image_id = i.id
                WHERE (i.user_id = ? OR e.image_id IS NULL)
                AND e.event_type = ?
                AND e.timestamp >= ?
                GROUP BY DATE(e.timestamp)
                ORDER BY date ASC
            """, (user_id, event_type, since))

            rows = await cursor.fetchall()

            # Fill in missing days with zero counts
            timeline = []
            current_date = since.date()
            end_date = datetime.now().date()

            # Create lookup dict from query results
            data_by_date = {row[0]: row[1] for row in rows}

            while current_date <= end_date:
                date_str = current_date.isoformat()
                count = data_by_date.get(date_str, 0)
                timeline.append({
                    "date": date_str,
                    "count": count
                })
                current_date += timedelta(days=1)

            return {
                "metric": metric,
                "period_days": days,
                "data": timeline
            }

    except Exception as e:
        logger.error(f"Failed to get analytics timeline: {str(e)}", exc_info=e)
        raise HTTPException(500, "Failed to retrieve timeline data")


@router.get("/top-images")
async def get_top_images(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    limit: int = Query(10, ge=1, le=50, description="Number of top images to return"),
    metric: str = Query("impressions", regex="^(impressions|clicks|views)$", description="Metric to rank by"),
    current_user: User = Depends(get_current_user_for_subdomain)
):
    """
    Get top performing images ranked by engagement.

    Returns images with highest impressions, clicks, or lightbox views.
    Impressions = times image entered viewport (50% visible)
    Clicks = gallery grid clicks
    Views = lightbox opens (full-screen views)
    """
    user_id = current_user.id
    since = datetime.now() - timedelta(days=days)

    # Map metric to event type
    event_type_map = {
        "impressions": "image_impression",
        "clicks": "gallery_click",
        "views": "lightbox_open"
    }
    event_type = event_type_map[metric]

    try:
        async with get_db_connection() as db:
            # Get top images with engagement metrics
            cursor = await db.execute("""
                SELECT
                    i.id,
                    i.title,
                    i.caption,
                    i.category,
                    i.filename,
                    COUNT(CASE WHEN e.event_type = 'image_impression' THEN 1 END) as impressions,
                    COUNT(CASE WHEN e.event_type = 'gallery_click' THEN 1 END) as clicks,
                    COUNT(CASE WHEN e.event_type = 'lightbox_open' THEN 1 END) as views
                FROM images i
                LEFT JOIN image_events e ON i.id = e.image_id AND e.timestamp >= ?
                WHERE i.user_id = ?
                AND i.published = 1
                GROUP BY i.id
                ORDER BY COUNT(CASE WHEN e.event_type = ? THEN 1 END) DESC
                LIMIT ?
            """, (since, user_id, event_type, limit))

            rows = await cursor.fetchall()

            # Get average view duration for each image (from lightbox_close events)
            top_images = []
            for row in rows:
                impressions = row[5]
                clicks = row[6]
                views = row[7]

                # Calculate CTR (clicks / impressions)
                ctr = (clicks / impressions) if impressions > 0 else 0

                # Calculate view rate (views / clicks)
                view_rate = (views / clicks) if clicks > 0 else 0

                # Get average duration from metadata
                duration_cursor = await db.execute("""
                    SELECT metadata FROM image_events
                    WHERE image_id = ?
                    AND event_type = 'lightbox_close'
                    AND timestamp >= ?
                    AND metadata IS NOT NULL
                """, (row[0], since))

                duration_rows = await duration_cursor.fetchall()
                durations = []
                for dr in duration_rows:
                    try:
                        import json
                        meta = json.loads(dr[0])
                        if 'duration' in meta:
                            durations.append(meta['duration'])
                    except:
                        pass

                avg_duration = sum(durations) / len(durations) if durations else 0

                top_images.append({
                    "id": row[0],
                    "title": row[1] or "Untitled",
                    "caption": row[2],
                    "category": row[3],
                    "thumbnail_url": f"/assets/gallery/{row[4]}",
                    "analytics": {
                        "impressions": impressions,
                        "clicks": clicks,
                        "views": views,
                        "ctr": round(ctr, 3),
                        "view_rate": round(view_rate, 3),
                        "avg_duration": round(avg_duration, 1)
                    }
                })

            return {
                "metric": metric,
                "period_days": days,
                "images": top_images
            }

    except Exception as e:
        logger.error(f"Failed to get top images: {str(e)}", exc_info=e)
        raise HTTPException(500, "Failed to retrieve top images")


@router.get("/referrers")
async def get_referrer_breakdown(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    limit: int = Query(10, ge=1, le=50, description="Number of top referrers to return"),
    current_user: User = Depends(get_current_user_for_subdomain)
):
    """
    Get traffic source breakdown (referrers).

    Returns top referrer URLs and their counts.
    """
    user_id = current_user.id
    since = datetime.now() - timedelta(days=days)

    try:
        async with get_db_connection() as db:
            cursor = await db.execute("""
                SELECT
                    CASE
                        WHEN e.referrer IS NULL OR e.referrer = '' THEN 'Direct / None'
                        ELSE e.referrer
                    END as referrer_group,
                    COUNT(*) as count
                FROM image_events e
                LEFT JOIN images i ON e.image_id = i.id
                WHERE (i.user_id = ? OR e.image_id IS NULL)
                AND e.timestamp >= ?
                GROUP BY referrer_group
                ORDER BY count DESC
                LIMIT ?
            """, (user_id, since, limit))

            rows = await cursor.fetchall()

            # Calculate total for percentage
            total = sum(row[1] for row in rows)

            referrers = []
            for row in rows:
                count = row[1]
                percentage = (count / total * 100) if total > 0 else 0

                referrers.append({
                    "referrer": row[0],
                    "count": count,
                    "percentage": round(percentage, 1)
                })

            return {
                "period_days": days,
                "total_events": total,
                "referrers": referrers
            }

    except Exception as e:
        logger.error(f"Failed to get referrer breakdown: {str(e)}", exc_info=e)
        raise HTTPException(500, "Failed to retrieve referrer data")


@router.get("/category-performance")
async def get_category_performance(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    current_user: User = Depends(get_current_user_for_subdomain)
):
    """
    Get engagement metrics broken down by image category.

    Returns performance metrics for each category (nature, wildlife, portrait, etc.)
    """
    user_id = current_user.id
    since = datetime.now() - timedelta(days=days)

    try:
        async with get_db_connection() as db:
            cursor = await db.execute("""
                SELECT
                    i.category,
                    COUNT(DISTINCT i.id) as image_count,
                    COUNT(CASE WHEN e.event_type = 'image_impression' THEN 1 END) as impressions,
                    COUNT(CASE WHEN e.event_type = 'gallery_click' THEN 1 END) as clicks,
                    COUNT(CASE WHEN e.event_type = 'lightbox_open' THEN 1 END) as views
                FROM images i
                LEFT JOIN image_events e ON i.id = e.image_id AND e.timestamp >= ?
                WHERE i.user_id = ?
                AND i.published = 1
                AND i.category IS NOT NULL
                GROUP BY i.category
                ORDER BY impressions DESC
            """, (since, user_id))

            rows = await cursor.fetchall()

            categories = []
            for row in rows:
                impressions = row[2]
                clicks = row[3]
                views = row[4]

                # Calculate metrics
                ctr = (clicks / impressions) if impressions > 0 else 0
                view_rate = (views / clicks) if clicks > 0 else 0

                categories.append({
                    "category": row[0],
                    "image_count": row[1],
                    "impressions": impressions,
                    "clicks": clicks,
                    "views": views,
                    "ctr": round(ctr, 3),
                    "view_rate": round(view_rate, 3)
                })

            return {
                "period_days": days,
                "categories": categories
            }

    except Exception as e:
        logger.error(f"Failed to get category performance: {str(e)}", exc_info=e)
        raise HTTPException(500, "Failed to retrieve category data")


@router.get("/scroll-depth")
async def get_scroll_depth(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    current_user: User = Depends(get_current_user_for_subdomain)
):
    """
    Get scroll depth distribution.

    Returns how many sessions reached each scroll milestone (25%, 50%, 75%, 100%).
    """
    user_id = current_user.id
    since = datetime.now() - timedelta(days=days)

    try:
        async with get_db_connection() as db:
            cursor = await db.execute("""
                SELECT metadata FROM image_events e
                LEFT JOIN images i ON e.image_id = i.id
                WHERE (i.user_id = ? OR e.image_id IS NULL)
                AND e.event_type = 'scroll_depth'
                AND e.timestamp >= ?
            """, (user_id, since))

            rows = await cursor.fetchall()

            # Parse metadata to extract depth values
            depth_counts = {25: 0, 50: 0, 75: 0, 100: 0}
            for row in rows:
                if row[0]:
                    try:
                        import json
                        meta = json.loads(row[0])
                        depth = meta.get('depth')
                        if depth in depth_counts:
                            depth_counts[depth] += 1
                    except:
                        pass

            # Get total sessions for percentage calculation
            cursor = await db.execute("""
                SELECT COUNT(DISTINCT session_id) FROM image_events e
                LEFT JOIN images i ON e.image_id = i.id
                WHERE (i.user_id = ? OR e.image_id IS NULL)
                AND e.timestamp >= ?
            """, (user_id, since))

            total_sessions = (await cursor.fetchone())[0]

            milestones = []
            for depth, count in sorted(depth_counts.items()):
                percentage = (count / total_sessions * 100) if total_sessions > 0 else 0
                milestones.append({
                    "depth": depth,
                    "sessions": count,
                    "percentage": round(percentage, 1)
                })

            return {
                "period_days": days,
                "total_sessions": total_sessions,
                "milestones": milestones
            }

    except Exception as e:
        logger.error(f"Failed to get scroll depth: {str(e)}", exc_info=e)
        raise HTTPException(500, "Failed to retrieve scroll depth data")


@router.get("/image/{image_id}")
async def get_image_analytics(
    image_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    current_user: User = Depends(get_current_user_for_subdomain)
):
    """
    Get detailed analytics for a specific image.

    Returns engagement metrics and timeline for single image.
    """
    user_id = current_user.id
    since = datetime.now() - timedelta(days=days)

    try:
        async with get_db_connection() as db:
            # Verify image ownership
            cursor = await db.execute(
                "SELECT user_id FROM images WHERE id = ?",
                (image_id,)
            )
            row = await cursor.fetchone()

            if not row:
                raise HTTPException(404, "Image not found")

            if row[0] != user_id and current_user.role != "admin":
                raise HTTPException(403, "Not authorized to view this image's analytics")

            # Get aggregate metrics
            cursor = await db.execute("""
                SELECT
                    COUNT(CASE WHEN event_type = 'page_view' THEN 1 END) as views,
                    COUNT(CASE WHEN event_type = 'gallery_click' THEN 1 END) as clicks,
                    COUNT(CASE WHEN event_type = 'lightbox_open' THEN 1 END) as lightbox_opens,
                    COUNT(DISTINCT session_id) as unique_visitors,
                    MIN(timestamp) as first_view,
                    MAX(timestamp) as last_view
                FROM image_events
                WHERE image_id = ?
                AND timestamp >= ?
            """, (image_id, since))

            metrics = await cursor.fetchone()

            views = metrics[0] or 0
            clicks = metrics[1] or 0
            click_rate = (clicks / views) if views > 0 else 0

            return {
                "image_id": image_id,
                "period_days": days,
                "views": views,
                "clicks": clicks,
                "lightbox_opens": metrics[2] or 0,
                "unique_visitors": metrics[3] or 0,
                "click_rate": round(click_rate, 3),
                "first_view": metrics[4],
                "last_view": metrics[5]
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get image analytics: {str(e)}", exc_info=e)
        raise HTTPException(500, "Failed to retrieve image analytics")
