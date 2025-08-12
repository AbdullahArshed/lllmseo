"""
Application configuration settings
"""
import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings"""
    
    # App Info
    app_name: str = "AI Brand Mention Tracker"
    app_version: str = "1.0.0"
    app_description: str = "Track brand mentions across platforms using AI insights"
    
    # Server Config
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    
    # Database
    database_url: str = "sqlite:///./brand_tracker.db"
    
    # OpenAI
    openai_api_key: str = ""
    
    # Real Reddit API Integration
    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_username: str = ""
    
    # Twitter/X API (Enterprise tier required for real monitoring)
    twitter_api_key: str = ""
    twitter_api_secret: str = ""
    twitter_bearer_token: str = ""
    
    # Third-party monitoring services
    brand24_api_key: str = ""
    kwatch_api_key: str = ""
    
    # Monitoring
    monitoring_interval: int = 60  # seconds (increased to reduce API calls)
    max_mentions_per_check: int = 5  # reduced to save tokens
    openai_free_tier_limit: int = 15  # API calls per session
    
    # AI-Generated Brand Tracking Platforms
    monitored_platforms: List[str] = [
        "ChatGPT",
        "Reddit", 
        "Twitter",
        "LinkedIn",
        "YouTube"
    ]
    
    # WebSocket
    ws_heartbeat_interval: int = 30
    ws_max_connections: int = 100
    
    # API
    api_prefix: str = "/api"
    cors_origins: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()