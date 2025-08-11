"""
Database models and operations for AI Brand Mention Tracker
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import sqlite3
import os

Base = declarative_base()

class BrandMention(Base):
    __tablename__ = "brand_mentions"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_name = Column(String(100), nullable=False, index=True)
    mention_text = Column(Text, nullable=False)
    platform = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    triggering_prompt = Column(Text, nullable=True)
    is_processed = Column(Boolean, default=False)
    sentiment_score = Column(String(20), nullable=True)  # positive, negative, neutral
    
    def to_dict(self):
        return {
            "id": self.id,
            "brand_name": self.brand_name,
            "mention_text": self.mention_text,
            "platform": self.platform,
            "timestamp": self.timestamp.isoformat(),
            "triggering_prompt": self.triggering_prompt,
            "is_processed": self.is_processed,
            "sentiment_score": self.sentiment_score
        }

class MonitoringConfig(Base):
    __tablename__ = "monitoring_config"
    
    id = Column(Integer, primary_key=True, index=True)
    brand_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    platforms = Column(Text, nullable=False)  # JSON string of platforms to monitor
    
    def to_dict(self):
        return {
            "id": self.id,
            "brand_name": self.brand_name,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "platforms": self.platforms
        }

# Database setup
DATABASE_URL = "sqlite:///./brand_tracker.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_database():
    """Initialize the database with tables"""
    create_tables()
    print("Database initialized successfully")

if __name__ == "__main__":
    init_database()