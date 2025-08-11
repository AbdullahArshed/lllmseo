"""
API routes for mention operations
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.database import get_db
from app.models.schemas import MentionResponse, StatsResponse, PlatformsResponse
from app.services.database import db_service
from app.core.config import settings

router = APIRouter(prefix="/mentions", tags=["mentions"])

@router.get("/", response_model=List[MentionResponse])
async def get_mentions(
    limit: int = Query(50, ge=1, le=100),
    brand_name: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get recent brand mentions"""
    mentions = db_service.get_mentions(db, limit=limit, brand_name=brand_name)
    return [
        MentionResponse(
            id=mention.id,
            brand_name=mention.brand_name,
            mention_text=mention.mention_text,
            platform=mention.platform,
            timestamp=mention.timestamp.isoformat(),
            triggering_prompt=mention.triggering_prompt,
            sentiment_score=mention.sentiment_score
        )
        for mention in mentions
    ]

@router.get("/{brand_name}", response_model=List[MentionResponse])
async def get_mentions_for_brand(
    brand_name: str,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get mentions for a specific brand"""
    mentions = db_service.get_mentions(db, limit=limit, brand_name=brand_name)
    return [
        MentionResponse(
            id=mention.id,
            brand_name=mention.brand_name,
            mention_text=mention.mention_text,
            platform=mention.platform,
            timestamp=mention.timestamp.isoformat(),
            triggering_prompt=mention.triggering_prompt,
            sentiment_score=mention.sentiment_score
        )
        for mention in mentions
    ]

@router.get("/platform/{platform_name}", response_model=List[MentionResponse])
async def get_mentions_by_platform(
    platform_name: str,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get mentions for a specific platform"""
    mentions = db_service.get_mentions_by_platform(db, platform_name, limit)
    return [
        MentionResponse(
            id=mention.id,
            brand_name=mention.brand_name,
            mention_text=mention.mention_text,
            platform=mention.platform,
            timestamp=mention.timestamp.isoformat(),
            triggering_prompt=mention.triggering_prompt,
            sentiment_score=mention.sentiment_score
        )
        for mention in mentions
    ]

@router.get("/search/", response_model=List[MentionResponse])
async def search_mentions(
    q: str = Query(..., min_length=2),
    brand_name: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search mentions by text content"""
    mentions = db_service.search_mentions(db, q, brand_name, limit)
    return [
        MentionResponse(
            id=mention.id,
            brand_name=mention.brand_name,
            mention_text=mention.mention_text,
            platform=mention.platform,
            timestamp=mention.timestamp.isoformat(),
            triggering_prompt=mention.triggering_prompt,
            sentiment_score=mention.sentiment_score
        )
        for mention in mentions
    ]

@router.delete("/{mention_id}")
async def delete_mention(
    mention_id: int,
    db: Session = Depends(get_db)
):
    """Delete a specific mention"""
    success = db_service.delete_mention(db, mention_id)
    if success:
        return {"success": True, "message": "Mention deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Mention not found")