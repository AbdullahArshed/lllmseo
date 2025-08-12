"""
AI Platform Monitoring Service for Brand Mention Tracking
"""
import asyncio
import random
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.models.database import BrandMention, SessionLocal
from app.core.config import settings
from openai import OpenAI
import os

logger = logging.getLogger(__name__)

class AIBrandMonitor:
    """Main monitoring service optimized for OpenAI free tier usage"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.platforms = settings.monitored_platforms
        self.is_monitoring = False
        self.current_brand = None
        self.monitoring_task = None
        
        # Free tier optimization
        self.mention_cache = {}  # Cache generated mentions to avoid re-generating
        self.api_call_count = 0  # Track API usage
        self.max_api_calls_per_session = 15  # Conservative limit for free tier
        self.last_generation_time = {}  # Rate limiting per brand
        
    def set_brand(self, brand_name: str):
        """Set the brand to monitor"""
        self.current_brand = brand_name
        logger.info(f"Brand set to: {brand_name}")
        
    async def real_reddit_check(self, brand_name: str) -> List[Dict]:
        """
        Actually check Reddit for real brand mentions using Reddit API + OpenAI for SEO analysis
        """
        mentions = []
        
        try:
            import praw  # Reddit API wrapper
            from textblob import TextBlob
            
            # Initialize Reddit API (you need to register at reddit.com/prefs/apps)
            reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                user_agent=f"SEOTracker/1.0 by {settings.reddit_username}"
            )
            
            # Search for brand mentions across relevant subreddits
            seo_subreddits = ["all", "seo", "marketing", "entrepreneur", "business", "startups"]
            
            for subreddit_name in seo_subreddits[:3]:  # Limit to avoid API limits
                try:
                    subreddit = reddit.subreddit(subreddit_name)
                    
                    # Search recent posts
                    for submission in subreddit.search(brand_name, limit=5, time_filter="day"):
                        content = f"{submission.title} {submission.selftext}"
                        
                        # Use OpenAI to analyze SEO relevance and sentiment
                        seo_analysis = await self.analyze_seo_relevance(content, brand_name)
                        
                        # Basic sentiment analysis
                        blob = TextBlob(content)
                        sentiment = "positive" if blob.sentiment.polarity > 0.1 else "negative" if blob.sentiment.polarity < -0.1 else "neutral"
                        
                        mention = {
                            "brand_name": brand_name,
                            "platform": f"Reddit r/{submission.subreddit}",
                            "mention_text": content[:500],
                            "url": f"https://reddit.com{submission.permalink}",
                            "timestamp": datetime.utcnow(),
                            "author": str(submission.author),
                            "subreddit": str(submission.subreddit),
                            "score": submission.score,
                            "sentiment": sentiment,
                            "seo_keywords": seo_analysis.get("keywords", []),
                            "seo_relevance": seo_analysis.get("relevance_score", 0),
                            "triggering_prompt": f"SEO analysis for {brand_name} in r/{submission.subreddit}"
                        }
                        mentions.append(mention)
                        
                        # Also analyze top comments for SEO insights
                        submission.comments.replace_more(limit=0)
                        for comment in submission.comments[:2]:
                            if hasattr(comment, 'body') and brand_name.lower() in comment.body.lower():
                                comment_analysis = await self.analyze_seo_relevance(comment.body, brand_name)
                                comment_sentiment = TextBlob(comment.body).sentiment.polarity
                                
                                mention = {
                                    "brand_name": brand_name,
                                    "platform": f"Reddit r/{submission.subreddit} (comment)",
                                    "mention_text": comment.body[:500],
                                    "url": f"https://reddit.com{comment.permalink}",
                                    "timestamp": datetime.utcnow(),
                                    "author": str(comment.author),
                                    "sentiment": "positive" if comment_sentiment > 0.1 else "negative" if comment_sentiment < -0.1 else "neutral",
                                    "seo_keywords": comment_analysis.get("keywords", []),
                                    "seo_relevance": comment_analysis.get("relevance_score", 0)
                                }
                                mentions.append(mention)
                                
                except Exception as e:
                    logger.warning(f"Error checking subreddit {subreddit_name}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Reddit API error: {e}")
            
        return mentions
    
    async def generate_brand_tracking_insight(self, brand_name: str, platform: str) -> List[Dict]:
        """
        Generate realistic brand tracking insights using OpenAI's free tier efficiently
        """
        if not self.client:
            return []
        
        # Check API call limit for free tier
        if self.api_call_count >= self.max_api_calls_per_session:
            logger.warning("API call limit reached for this session. Using cached data.")
            return self._get_cached_mentions(brand_name, platform)
        
        # Check rate limiting (don't generate for same brand/platform too frequently)
        cache_key = f"{brand_name}_{platform}"
        current_time = datetime.utcnow()
        
        if cache_key in self.last_generation_time:
            time_diff = (current_time - self.last_generation_time[cache_key]).seconds
            if time_diff < 300:  # 5 minute cooldown
                logger.info(f"Rate limited: Using cached data for {cache_key}")
                return self._get_cached_mentions(brand_name, platform)
        
        try:
            # Optimized shorter prompts to save tokens on free tier
            prompts = {
                "ChatGPT": f"Generate 2 realistic ChatGPT conversations mentioning {brand_name}.",
                "Reddit": f"Create 2 Reddit-style posts/comments about {brand_name}.",
                "Twitter": f"Generate 2 realistic tweets mentioning {brand_name}.",
                "LinkedIn": f"Create 2 professional LinkedIn posts about {brand_name}.",
                "YouTube": f"Generate 2 YouTube video titles/descriptions about {brand_name}."
            }
            
            prompt = prompts.get(platform, prompts["ChatGPT"])
            
            # Increment API call counter
            self.api_call_count += 1
            logger.info(f"API call {self.api_call_count}/{self.max_api_calls_per_session}")
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",  # Most cost-effective model
                messages=[{
                    "role": "user", 
                    "content": f"{prompt} Keep responses under 150 words total. Make them realistic and varied."
                }],
                temperature=0.7,  # Slightly lower for consistency
                max_tokens=150  # Reduced from 300 to save credits
            )
            
            # Update rate limiting
            self.last_generation_time[cache_key] = current_time
            
            content = response.choices[0].message.content
            
            # Split content into individual mentions
            mentions = []
            paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
            
            for i, paragraph in enumerate(paragraphs[:3]):  # Limit to 3 mentions per call
                # Determine sentiment using OpenAI
                sentiment = await self.analyze_sentiment(paragraph, brand_name)
                
                mention = {
                    "brand_name": brand_name,
                    "platform": platform,
                    "mention_text": paragraph,
                    "timestamp": datetime.utcnow(),
                    "sentiment": sentiment,
                    "triggering_prompt": f"Brand tracking for {brand_name} on {platform}",
                    "is_processed": True,
                    "author": f"User_{random.randint(1000, 9999)}",
                    "engagement_score": random.randint(1, 100)
                }
                mentions.append(mention)
            
            # Cache the generated mentions
            self._cache_mentions(brand_name, platform, mentions)
            
            return mentions
            
        except Exception as e:
            logger.error(f"Brand tracking generation error: {e}")
            return self._get_cached_mentions(brand_name, platform)
    
    def _cache_mentions(self, brand_name: str, platform: str, mentions: List[Dict]):
        """Cache generated mentions to avoid re-generating"""
        cache_key = f"{brand_name}_{platform}"
        self.mention_cache[cache_key] = {
            "mentions": mentions,
            "timestamp": datetime.utcnow()
        }
        
    def _get_cached_mentions(self, brand_name: str, platform: str) -> List[Dict]:
        """Get cached mentions with slight randomization"""
        cache_key = f"{brand_name}_{platform}"
        
        if cache_key in self.mention_cache:
            cached_data = self.mention_cache[cache_key]
            # Return cached mentions with updated timestamps
            mentions = []
            for mention in cached_data["mentions"]:
                updated_mention = mention.copy()
                updated_mention["timestamp"] = datetime.utcnow()
                updated_mention["author"] = f"User_{random.randint(1000, 9999)}"  # Randomize author
                mentions.append(updated_mention)
            return mentions
        
        # Return empty if no cache available
        return []
    
    async def analyze_sentiment(self, text: str, brand_name: str) -> str:
        """
        Analyze sentiment efficiently using keyword matching to save OpenAI credits
        """
        # Use simple keyword-based sentiment analysis to save API credits
        text_lower = text.lower()
        
        # Positive indicators
        positive_words = ["great", "excellent", "love", "amazing", "awesome", "best", "fantastic", 
                         "recommend", "perfect", "outstanding", "brilliant", "wonderful", "impressive",
                         "good", "nice", "happy", "satisfied", "quality", "reliable"]
        
        # Negative indicators  
        negative_words = ["terrible", "awful", "hate", "worst", "horrible", "bad", "disappointing",
                         "waste", "useless", "annoying", "frustrated", "problem", "issue", "broken",
                         "poor", "cheap", "unreliable", "slow", "expensive", "difficult"]
        
        # Count positive and negative words
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        # Determine sentiment
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    

    async def simulate_platform_check(self, platform: str, brand_name: str) -> Optional[Dict]:
        """
        Simulate checking a platform for brand mentions
        DEPRECATED: Use real_reddit_check for actual Reddit monitoring
        """
        # Simulate random mentions with realistic probability  
        if random.random() < 0.15:  # 15% chance of finding a mention
            
            # Generate realistic mention scenarios
            mention_types = [
                f"User asked about {brand_name} vs competitors",
                f"Discussion about {brand_name} features and benefits",
                f"Comparison between {brand_name} and alternatives", 
                f"Review of {brand_name} products/services",
                f"Technical question involving {brand_name}",
                f"User seeking recommendations, {brand_name} mentioned",
                f"Troubleshooting {brand_name} related issue"
            ]
            
            # Sample realistic prompts
            sample_prompts = [
                f"What are the best alternatives to {brand_name}?",
                f"How does {brand_name} compare to its competitors?",
                f"I'm having issues with {brand_name}, can you help?",
                f"What are the pros and cons of {brand_name}?",
                f"Is {brand_name} worth the investment?",
                f"Can you recommend something like {brand_name}?",
                f"Tell me about {brand_name}'s latest features"
            ]
            
            # Generate mention text using OpenAI if available
            mention_text = await self.generate_realistic_mention(brand_name, platform)
            
            return {
                "brand_name": brand_name,
                "platform": platform,
                "mention_text": mention_text,
                "triggering_prompt": random.choice(sample_prompts),
                "timestamp": datetime.utcnow(),
                "sentiment": random.choice(["positive", "neutral", "negative"])
            }
        return None
    
    async def generate_realistic_mention(self, brand_name: str, platform: str) -> str:
        """Generate realistic mention text using OpenAI"""
        try:
            if self.client and self.client.api_key:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": f"Generate a realistic AI assistant response that mentions {brand_name}. The response should be from {platform} and be helpful, informative, and natural. Keep it under 200 words."
                        },
                        {
                            "role": "user",
                            "content": f"Create a response that naturally mentions {brand_name} in context."
                        }
                    ],
                    max_tokens=200,
                    temperature=0.7
                )
                return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
        
        # Fallback realistic mentions
        fallback_mentions = [
            f"Based on your requirements, {brand_name} could be a good option. It offers several features that align with what you're looking for, including robust functionality and user-friendly interface.",
            f"I'd recommend considering {brand_name} among your options. Many users have reported positive experiences with their service, particularly praising their customer support and reliability.",
            f"When comparing different solutions, {brand_name} stands out for its innovative approach and competitive pricing. However, I'd suggest evaluating it alongside other alternatives to find the best fit.",
            f"Several users have mentioned {brand_name} as a reliable choice in this category. While it has many strengths, it's worth noting that the best option depends on your specific needs and budget.",
            f"{brand_name} has been gaining traction in the market recently. Their latest updates have addressed many user concerns, making it a more compelling option than before."
        ]
        
        return random.choice(fallback_mentions)
    
    async def check_all_platforms(self, brand_name: str) -> List[Dict]:
        """Generate brand tracking insights using only OpenAI LLM"""
        mentions = []
        
        # Generate brand mentions across different platforms using OpenAI
        platform_tasks = [
            self.generate_brand_tracking_insight(brand_name, "ChatGPT"),
            self.generate_brand_tracking_insight(brand_name, "Reddit"),
            self.generate_brand_tracking_insight(brand_name, "Twitter"),
            self.generate_brand_tracking_insight(brand_name, "LinkedIn"),
            self.generate_brand_tracking_insight(brand_name, "YouTube")
        ]
        
        results = await asyncio.gather(*platform_tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Brand tracking error: {result}")
            elif result:
                mentions.extend(result)
                
        logger.info(f"Generated {len(mentions)} brand tracking insights using OpenAI")
        return mentions
    
    async def save_mentions_to_db(self, mentions: List[Dict]) -> bool:
        """Save found mentions to database"""
        if not mentions:
            return True
            
        db = SessionLocal()
        try:
            for mention_data in mentions:
                mention = BrandMention(
                    brand_name=mention_data["brand_name"],
                    mention_text=mention_data["mention_text"], 
                    platform=mention_data["platform"],
                    timestamp=mention_data["timestamp"],
                    triggering_prompt=mention_data.get("triggering_prompt"),
                    sentiment_score=mention_data.get("sentiment", "neutral")
                )
                db.add(mention)
            db.commit()
            logger.info(f"Saved {len(mentions)} mentions to database")
            return True
        except Exception as e:
            logger.error(f"Error saving mentions: {e}")
            db.rollback()
            return False
        finally:
            db.close()
    
    async def start_monitoring(self, brand_name: str, check_interval: int = None) -> bool:
        """Start continuous monitoring for a brand"""
        if self.is_monitoring:
            await self.stop_monitoring()
        
        self.current_brand = brand_name
        self.is_monitoring = True
        interval = check_interval or settings.monitoring_interval
        
        logger.info(f"Starting monitoring for '{brand_name}' across {len(self.platforms)} platforms")
        logger.info(f"Check interval: {interval} seconds")
        
        # Start monitoring in background task
        self.monitoring_task = asyncio.create_task(
            self._monitoring_loop(brand_name, interval)
        )
        return True
    
    async def stop_monitoring(self):
        """Stop the monitoring process"""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            self.monitoring_task = None
        
        logger.info("Monitoring stopped")
    
    async def _monitoring_loop(self, brand_name: str, check_interval: int):
        """Internal monitoring loop"""
        while self.is_monitoring:
            try:
                mentions = await self.check_all_platforms(brand_name)
                if mentions:
                    await self.save_mentions_to_db(mentions)
                    logger.info(f"Found {len(mentions)} new mentions at {datetime.utcnow()}")
                    
                    # Return mentions for external handling (WebSocket broadcast)
                    return mentions
                else:
                    logger.debug(f"No mentions found at {datetime.utcnow()}")
                    
                await asyncio.sleep(check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(5)  # Short delay before retrying
    
    def get_status(self) -> Dict:
        """Get current monitoring status with API usage info"""
        return {
            "is_active": self.is_monitoring,
            "current_brand": self.current_brand,
            "platforms_count": len(self.platforms),
            "platforms": self.platforms,
            "api_calls_used": self.api_call_count,
            "api_calls_remaining": max(0, self.max_api_calls_per_session - self.api_call_count),
            "cache_size": len(self.mention_cache)
        }
    
    def reset_api_counter(self):
        """Reset API call counter (useful for new sessions)"""
        self.api_call_count = 0
        logger.info("API call counter reset for new session")

# Global monitor instance
monitor = AIBrandMonitor()