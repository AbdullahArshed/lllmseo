"""
Database service layer for brand mention operations
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from app.models.database import BrandMention, MonitoringConfig, get_db, SessionLocal
from app.models.schemas import MentionResponse, StatsResponse

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service layer for database operations"""
    
    @staticmethod
    def get_mentions(
        db: Session, 
        limit: int = 50, 
        brand_name: Optional[str] = None
    ) -> List[BrandMention]:
        """Get brand mentions with optional filtering"""
        query = db.query(BrandMention)
        
        if brand_name:
            query = query.filter(BrandMention.brand_name == brand_name)
        
        return query.order_by(desc(BrandMention.timestamp)).limit(limit).all()
    
    @staticmethod
    def get_mention_by_id(db: Session, mention_id: int) -> Optional[BrandMention]:
        """Get a specific mention by ID"""
        return db.query(BrandMention).filter(BrandMention.id == mention_id).first()
    
    @staticmethod
    def create_mention(
        db: Session,
        brand_name: str,
        mention_text: str,
        platform: str,
        triggering_prompt: Optional[str] = None,
        sentiment_score: Optional[str] = None
    ) -> BrandMention:
        """Create a new brand mention"""
        mention = BrandMention(
            brand_name=brand_name,
            mention_text=mention_text,
            platform=platform,
            timestamp=datetime.utcnow(),
            triggering_prompt=triggering_prompt,
            sentiment_score=sentiment_score
        )
        
        db.add(mention)
        db.commit()
        db.refresh(mention)
        logger.info(f"Created mention for {brand_name} on {platform}")
        return mention
    
    @staticmethod
    def delete_mention(db: Session, mention_id: int) -> bool:
        """Delete a mention by ID"""
        mention = db.query(BrandMention).filter(BrandMention.id == mention_id).first()
        if mention:
            db.delete(mention)
            db.commit()
            logger.info(f"Deleted mention {mention_id}")
            return True
        return False
    
    @staticmethod
    def get_stats(db: Session, brand_name: Optional[str] = None) -> StatsResponse:
        """Get monitoring statistics"""
        # Base queries
        total_query = db.query(BrandMention)
        recent_query = db.query(BrandMention)
        
        # Filter by brand if specified
        if brand_name:
            total_query = total_query.filter(BrandMention.brand_name == brand_name)
            recent_query = recent_query.filter(BrandMention.brand_name == brand_name)
        
        # Calculate stats
        total_mentions = total_query.count()
        
        # Recent mentions (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(hours=24)
        recent_mentions = recent_query.filter(
            BrandMention.timestamp >= yesterday
        ).count()
        
        return StatsResponse(
            total_mentions=total_mentions,
            recent_mentions=recent_mentions,
            is_monitoring=False,  # This will be set by the calling service
            current_brand=brand_name
        )
    
    @staticmethod
    def get_mentions_by_platform(db: Session, platform: str, limit: int = 50) -> List[BrandMention]:
        """Get mentions for a specific platform"""
        return db.query(BrandMention).filter(
            BrandMention.platform == platform
        ).order_by(desc(BrandMention.timestamp)).limit(limit).all()
    
    @staticmethod
    def get_mentions_by_timeframe(
        db: Session, 
        hours: int = 24, 
        brand_name: Optional[str] = None
    ) -> List[BrandMention]:
        """Get mentions within a specific timeframe"""
        time_threshold = datetime.utcnow() - timedelta(hours=hours)
        query = db.query(BrandMention).filter(BrandMention.timestamp >= time_threshold)
        
        if brand_name:
            query = query.filter(BrandMention.brand_name == brand_name)
        
        return query.order_by(desc(BrandMention.timestamp)).all()
    
    @staticmethod
    def get_platform_stats(db: Session, brand_name: Optional[str] = None) -> dict:
        """Get statistics grouped by platform"""
        query = db.query(
            BrandMention.platform,
            func.count(BrandMention.id).label('count')
        )
        
        if brand_name:
            query = query.filter(BrandMention.brand_name == brand_name)
        
        results = query.group_by(BrandMention.platform).all()
        
        return {platform: count for platform, count in results}
    
    @staticmethod
    def get_sentiment_stats(db: Session, brand_name: Optional[str] = None) -> dict:
        """Get sentiment analysis statistics"""
        query = db.query(
            BrandMention.sentiment_score,
            func.count(BrandMention.id).label('count')
        )
        
        if brand_name:
            query = query.filter(BrandMention.brand_name == brand_name)
        
        results = query.filter(
            BrandMention.sentiment_score.isnot(None)
        ).group_by(BrandMention.sentiment_score).all()
        
        return {sentiment: count for sentiment, count in results}
    
    @staticmethod
    def search_mentions(
        db: Session, 
        search_term: str, 
        brand_name: Optional[str] = None,
        limit: int = 50
    ) -> List[BrandMention]:
        """Search mentions by text content"""
        query = db.query(BrandMention).filter(
            BrandMention.mention_text.contains(search_term)
        )
        
        if brand_name:
            query = query.filter(BrandMention.brand_name == brand_name)
        
        return query.order_by(desc(BrandMention.timestamp)).limit(limit).all()
    
    @staticmethod
    def create_monitoring_config(
        db: Session,
        brand_name: str,
        platforms: List[str]
    ) -> MonitoringConfig:
        """Create a monitoring configuration"""
        import json
        
        config = MonitoringConfig(
            brand_name=brand_name,
            platforms=json.dumps(platforms),
            is_active=True
        )
        
        db.add(config)
        db.commit()
        db.refresh(config)
        logger.info(f"Created monitoring config for {brand_name}")
        return config
    
    @staticmethod
    def get_active_configs(db: Session) -> List[MonitoringConfig]:
        """Get all active monitoring configurations"""
        return db.query(MonitoringConfig).filter(
            MonitoringConfig.is_active == True
        ).all()
    
    @staticmethod
    def deactivate_config(db: Session, config_id: int) -> bool:
        """Deactivate a monitoring configuration"""
        config = db.query(MonitoringConfig).filter(
            MonitoringConfig.id == config_id
        ).first()
        
        if config:
            config.is_active = False
            db.commit()
            logger.info(f"Deactivated monitoring config {config_id}")
            return True
        return False

# Global database service instance
db_service = DatabaseService()