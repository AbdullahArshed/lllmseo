"""
API routes for statistics and analytics
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.models.database import get_db
from app.models.schemas import StatsResponse, PlatformsResponse
from app.services.database import db_service
from app.services.monitoring import monitor
from app.core.config import settings

router = APIRouter(prefix="/stats", tags=["statistics"])

@router.get("/", response_model=StatsResponse)
async def get_stats(
    brand_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get monitoring statistics"""
    stats = db_service.get_stats(db, brand_name)
    
    # Update with current monitoring status
    status = monitor.get_status()
    stats.is_monitoring = status["is_active"]
    stats.current_brand = status["current_brand"]
    
    return stats

@router.get("/platforms", response_model=PlatformsResponse)
async def get_platforms():
    """Get list of monitored platforms"""
    return PlatformsResponse(
        platforms=settings.monitored_platforms,
        count=len(settings.monitored_platforms)
    )

@router.get("/platforms/breakdown")
async def get_platform_breakdown(
    brand_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get mention count breakdown by platform"""
    platform_stats = db_service.get_platform_stats(db, brand_name)
    return {
        "platform_breakdown": platform_stats,
        "total_platforms": len(settings.monitored_platforms),
        "active_platforms": len(platform_stats)
    }

@router.get("/sentiment")
async def get_sentiment_analysis(
    brand_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get sentiment analysis statistics"""
    sentiment_stats = db_service.get_sentiment_stats(db, brand_name)
    
    total_analyzed = sum(sentiment_stats.values())
    
    return {
        "sentiment_breakdown": sentiment_stats,
        "total_analyzed": total_analyzed,
        "sentiment_percentages": {
            sentiment: (count / total_analyzed * 100) if total_analyzed > 0 else 0
            for sentiment, count in sentiment_stats.items()
        }
    }

@router.get("/timeframe")
async def get_timeframe_stats(
    hours: int = Query(24, ge=1, le=168),  # Max 1 week
    brand_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get mentions within a specific timeframe"""
    mentions = db_service.get_mentions_by_timeframe(db, hours, brand_name)
    
    # Group by hour for trending
    from collections import defaultdict
    from datetime import datetime, timedelta
    
    hourly_counts = defaultdict(int)
    for mention in mentions:
        hour_key = mention.timestamp.replace(minute=0, second=0, microsecond=0)
        hourly_counts[hour_key] += 1
    
    return {
        "total_mentions": len(mentions),
        "timeframe_hours": hours,
        "brand_name": brand_name,
        "hourly_breakdown": [
            {
                "hour": hour.isoformat(),
                "count": count
            }
            for hour, count in sorted(hourly_counts.items())
        ]
    }