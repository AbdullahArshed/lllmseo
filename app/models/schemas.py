"""
Pydantic models for API request/response schemas
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class BrandConfig(BaseModel):
    """Schema for brand monitoring configuration"""
    brand_name: str
    platforms: List[str] = [
        "ChatGPT", 
        "Perplexity", 
        "Gemini", 
        "Google Overviews AI", 
        "Grok", 
        "Claude", 
        "Bing Copilot"
    ]

class MentionResponse(BaseModel):
    """Schema for brand mention response"""
    id: int
    brand_name: str
    mention_text: str
    platform: str
    timestamp: str
    triggering_prompt: Optional[str] = None
    sentiment_score: Optional[str] = None

class MonitoringStatus(BaseModel):
    """Schema for monitoring status"""
    is_active: bool
    current_brand: Optional[str] = None
    start_time: Optional[datetime] = None
    platforms_count: int

class ApiResponse(BaseModel):
    """Generic API response schema"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None

class StatsResponse(BaseModel):
    """Schema for statistics response"""
    total_mentions: int
    recent_mentions: int
    is_monitoring: bool
    current_brand: Optional[str] = None

class PlatformsResponse(BaseModel):
    """Schema for platforms response"""
    platforms: List[str]
    count: int

class WebSocketMessage(BaseModel):
    """Schema for WebSocket messages"""
    type: str  # 'mention', 'status', 'error'
    data: dict