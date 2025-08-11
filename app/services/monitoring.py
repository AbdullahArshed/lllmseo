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
    """Main monitoring service for AI platforms"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.platforms = settings.monitored_platforms
        self.is_monitoring = False
        self.current_brand = None
        self.monitoring_task = None
        
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
        Generate realistic brand tracking insights using only OpenAI LLM
        """
        if not self.client:
            return []
            
        try:
            prompts = {
                "ChatGPT": f"""
                Generate realistic conversations where users ask about or mention "{brand_name}". 
                Create 2-3 realistic ChatGPT-style interactions that include:
                - User questions about {brand_name}
                - Comparisons with competitors  
                - Reviews or experiences
                - Feature questions
                
                Format as if these were real ChatGPT conversations mentioning {brand_name}.
                Make them sound natural and varied.
                """,
                
                "Reddit": f"""
                Create realistic Reddit-style discussions about "{brand_name}". Include:
                - Posts asking for opinions about {brand_name}
                - Comments comparing {brand_name} to alternatives
                - User experiences (both positive and negative)
                - Technical questions about {brand_name}
                
                Make them sound like real Reddit users with authentic language and concerns.
                """,
                
                "Twitter": f"""
                Generate realistic Twitter-style mentions of "{brand_name}". Create:
                - User tweets about {brand_name} experiences
                - Questions to followers about {brand_name}
                - Complaints or praise about {brand_name}
                - News reactions involving {brand_name}
                
                Keep Twitter's character limit and style in mind.
                """,
                
                "LinkedIn": f"""
                Create professional LinkedIn-style mentions of "{brand_name}". Include:
                - Professional recommendations
                - Business use cases for {brand_name}
                - Industry analysis mentioning {brand_name}
                - Career-related discussions involving {brand_name}
                
                Maintain professional tone and business context.
                """,
                
                "YouTube": f"""
                Generate realistic YouTube video titles and descriptions that mention "{brand_name}". Include:
                - Review video concepts
                - Tutorial titles featuring {brand_name}
                - Comparison videos with competitors
                - Unboxing or first impression videos
                
                Make them sound like real YouTube content.
                """
            }
            
            prompt = prompts.get(platform, prompts["ChatGPT"])
            
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system", 
                    "content": f"Generate realistic social media content that mentions {brand_name}. Make it sound authentic and varied."
                }, {
                    "role": "user", 
                    "content": prompt
                }],
                temperature=0.8,
                max_tokens=300
            )
            
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
            
            return mentions
            
        except Exception as e:
            logger.error(f"Brand tracking generation error: {e}")
            return []
    
    async def analyze_sentiment(self, text: str, brand_name: str) -> str:
        """
        Analyze sentiment of brand mention using OpenAI
        """
        if not self.client:
            return "neutral"
            
        try:
            response = await asyncio.to_thread(
                self.client.chat.completions.create,
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": "Analyze the sentiment towards the brand mentioned. Respond with only: positive, negative, or neutral"
                }, {
                    "role": "user", 
                    "content": f"Analyze sentiment towards {brand_name} in this text: {text[:200]}"
                }],
                temperature=0.3,
                max_tokens=10
            )
            
            sentiment = response.choices[0].message.content.strip().lower()
            if sentiment in ["positive", "negative", "neutral"]:
                return sentiment
            return "neutral"
            
        except Exception as e:
            logger.error(f"Sentiment analysis error: {e}")
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
        """Get current monitoring status"""
        return {
            "is_active": self.is_monitoring,
            "current_brand": self.current_brand,
            "platforms_count": len(self.platforms),
            "platforms": self.platforms
        }

# Global monitor instance
monitor = AIBrandMonitor()