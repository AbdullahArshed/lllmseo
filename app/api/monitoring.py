"""
API routes for monitoring operations
"""
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
import json
import logging

from app.models.database import get_db
from app.models.schemas import BrandConfig, ApiResponse, MonitoringStatus
from app.services.monitoring import monitor
from app.services.database import db_service
from app.core.websocket import manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

@router.post("/start", response_model=ApiResponse)
async def start_monitoring(
    config: BrandConfig, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """Start monitoring for a specific brand"""
    try:
        # Stop existing monitoring if active
        if monitor.is_monitoring:
            await monitor.stop_monitoring()
        
        # Save monitoring config to database
        db_config = db_service.create_monitoring_config(
            db=db,
            brand_name=config.brand_name,
            platforms=config.platforms
        )
        
        # Start monitoring in background
        success = await monitor.start_monitoring(config.brand_name)
        
        if success:
            # Broadcast status to connected clients
            await manager.broadcast_status(True, config.brand_name)
            
            # Start background monitoring loop
            background_tasks.add_task(monitoring_background_task, config.brand_name)
            
            logger.info(f"Started monitoring for {config.brand_name}")
            return ApiResponse(
                success=True, 
                message=f"Started monitoring for {config.brand_name}"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to start monitoring")
    
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        return ApiResponse(success=False, error=str(e))

@router.post("/stop", response_model=ApiResponse)
async def stop_monitoring():
    """Stop monitoring"""
    try:
        await monitor.stop_monitoring()
        
        # Broadcast status to connected clients
        await manager.broadcast_status(False, None)
        
        logger.info("Monitoring stopped")
        return ApiResponse(success=True, message="Monitoring stopped")
    
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        return ApiResponse(success=False, error=str(e))

@router.get("/status", response_model=MonitoringStatus)
async def get_monitoring_status():
    """Get current monitoring status"""
    status = monitor.get_status()
    return MonitoringStatus(
        is_active=status["is_active"],
        current_brand=status["current_brand"],
        platforms_count=status["platforms_count"]
    )

async def monitoring_background_task(brand_name: str):
    """Background task for continuous monitoring"""
    while monitor.is_monitoring:
        try:
            # Check for mentions
            mentions = await monitor.check_all_platforms(brand_name)
            
            if mentions:
                # Save to database
                await monitor.save_mentions_to_db(mentions)
                
                # Broadcast to connected clients
                for mention in mentions:
                    mention_dict = {
                        "brand_name": mention["brand_name"],
                        "mention_text": mention["mention_text"],
                        "platform": mention["platform"],
                        "timestamp": mention["timestamp"].isoformat(),
                        "triggering_prompt": mention.get("triggering_prompt"),
                        "sentiment_score": mention.get("sentiment")
                    }
                    
                    await manager.broadcast_mention(mention_dict)
            
            # Wait before next check
            import asyncio
            from app.core.config import settings
            await asyncio.sleep(settings.monitoring_interval)
            
        except Exception as e:
            logger.error(f"Monitoring background task error: {e}")
            await asyncio.sleep(5)