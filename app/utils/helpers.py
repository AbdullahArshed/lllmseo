"""
Utility functions and helpers
"""
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

def validate_brand_name(brand_name: str) -> bool:
    """Validate brand name format"""
    if not brand_name or not brand_name.strip():
        return False
    
    # Remove extra spaces and validate length
    cleaned = re.sub(r'\s+', ' ', brand_name.strip())
    if len(cleaned) < 2 or len(cleaned) > 100:
        return False
    
    # Check for valid characters (letters, numbers, spaces, common punctuation)
    if not re.match(r'^[a-zA-Z0-9\s\-_&.]+$', cleaned):
        return False
    
    return True

def clean_brand_name(brand_name: str) -> str:
    """Clean and normalize brand name"""
    if not brand_name:
        return ""
    
    # Remove extra spaces and normalize
    cleaned = re.sub(r'\s+', ' ', brand_name.strip())
    return cleaned

def format_timestamp(timestamp: datetime) -> str:
    """Format timestamp for display"""
    now = datetime.utcnow()
    diff = now - timestamp
    
    if diff.days > 0:
        return f"{diff.days} days ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hours ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minutes ago"
    else:
        return "Just now"

def sanitize_mention_text(text: str) -> str:
    """Sanitize mention text for safe display"""
    if not text:
        return ""
    
    # Remove any potentially harmful content
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
    
    # Limit length
    if len(text) > 2000:
        text = text[:1997] + "..."
    
    return text.strip()

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Extract keywords from mention text"""
    if not text:
        return []
    
    # Simple keyword extraction (could be enhanced with NLP)
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    
    # Filter out common stop words
    stop_words = {
        'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 
        'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 
        'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'who', 'boy', 
        'did', 'she', 'use', 'way', 'too', 'any', 'each', 'which', 'their'
    }
    
    keywords = [word for word in words if word not in stop_words and len(word) > 3]
    
    # Get unique keywords and limit count
    unique_keywords = list(dict.fromkeys(keywords))[:max_keywords]
    
    return unique_keywords

def calculate_sentiment_score(positive: int, negative: int, neutral: int) -> Dict[str, float]:
    """Calculate sentiment percentages"""
    total = positive + negative + neutral
    
    if total == 0:
        return {"positive": 0.0, "negative": 0.0, "neutral": 0.0}
    
    return {
        "positive": round((positive / total) * 100, 1),
        "negative": round((negative / total) * 100, 1),
        "neutral": round((neutral / total) * 100, 1)
    }

def generate_mention_summary(mentions: List[Dict]) -> Dict:
    """Generate summary statistics for mentions"""
    if not mentions:
        return {
            "total_mentions": 0,
            "platforms": [],
            "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
            "time_range": None,
            "top_keywords": []
        }
    
    # Platform distribution
    platforms = list(set(mention.get("platform") for mention in mentions))
    
    # Sentiment distribution
    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
    for mention in mentions:
        sentiment = mention.get("sentiment_score", "neutral")
        if sentiment in sentiment_counts:
            sentiment_counts[sentiment] += 1
    
    # Time range
    timestamps = [
        datetime.fromisoformat(mention["timestamp"].replace("Z", "+00:00")) 
        for mention in mentions 
        if mention.get("timestamp")
    ]
    
    time_range = None
    if timestamps:
        earliest = min(timestamps)
        latest = max(timestamps)
        time_range = {
            "earliest": earliest.isoformat(),
            "latest": latest.isoformat(),
            "span_hours": (latest - earliest).total_seconds() / 3600
        }
    
    # Extract top keywords
    all_text = " ".join(mention.get("mention_text", "") for mention in mentions)
    top_keywords = extract_keywords(all_text, max_keywords=15)
    
    return {
        "total_mentions": len(mentions),
        "platforms": platforms,
        "platform_count": len(platforms),
        "sentiment_distribution": sentiment_counts,
        "sentiment_percentages": calculate_sentiment_score(
            sentiment_counts["positive"],
            sentiment_counts["negative"], 
            sentiment_counts["neutral"]
        ),
        "time_range": time_range,
        "top_keywords": top_keywords
    }

def is_valid_platform(platform: str, valid_platforms: List[str]) -> bool:
    """Check if platform is in the list of valid platforms"""
    return platform in valid_platforms

def log_performance(func_name: str, duration: float, additional_info: str = ""):
    """Log performance metrics"""
    logger.info(f"Performance: {func_name} took {duration:.3f}s {additional_info}")

def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def normalize_search_query(query: str) -> str:
    """Normalize search query for better matching"""
    if not query:
        return ""
    
    # Convert to lowercase and remove extra spaces
    normalized = re.sub(r'\s+', ' ', query.lower().strip())
    
    # Remove special characters except spaces and dashes
    normalized = re.sub(r'[^\w\s\-]', '', normalized)
    
    return normalized

class RateLimiter:
    """Simple rate limiter for API calls"""
    
    def __init__(self, max_calls: int, time_window: int):
        self.max_calls = max_calls
        self.time_window = time_window  # in seconds
        self.calls = []
    
    def is_allowed(self) -> bool:
        """Check if a call is allowed under rate limiting"""
        now = datetime.utcnow()
        
        # Remove old calls outside the time window
        cutoff = now - timedelta(seconds=self.time_window)
        self.calls = [call_time for call_time in self.calls if call_time > cutoff]
        
        # Check if we're under the limit
        if len(self.calls) < self.max_calls:
            self.calls.append(now)
            return True
        
        return False
    
    def time_until_next_allowed(self) -> int:
        """Get seconds until next call is allowed"""
        if len(self.calls) < self.max_calls:
            return 0
        
        oldest_call = min(self.calls)
        next_allowed = oldest_call + timedelta(seconds=self.time_window)
        diff = next_allowed - datetime.utcnow()
        
        return max(0, int(diff.total_seconds()))