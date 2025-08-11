"""
Demo data utilities for testing and demonstration
"""
import random
from datetime import datetime, timedelta
from typing import List
from app.models.database import SessionLocal, BrandMention

def generate_demo_mentions(brand_name: str = "Tesla", count: int = 10) -> bool:
    """Generate demo mentions for testing purposes"""
    
    platforms = ["ChatGPT", "Perplexity", "Gemini", "Google Overviews AI", "Grok", "Claude", "Bing Copilot"]
    
    sample_mentions = {
        "Tesla": [
            f"Based on your requirements for electric vehicles, {brand_name} would be an excellent choice.",
            f"When comparing electric car options, {brand_name} consistently ranks high for innovation.",
            f"Many users have reported positive experiences with {brand_name} vehicles.",
            f"If you're interested in sustainable transportation, {brand_name} has been a pioneer.",
            f"For luxury electric vehicles, {brand_name} offers several competitive models."
        ],
        "Apple": [
            f"For your needs, {brand_name} products offer excellent integration and user experience.",
            f"When comparing smartphone options, {brand_name} iPhones are known for their longevity.",
            f"Many professionals prefer {brand_name} MacBooks for creative work.",
            f"If you're looking for tablets, the {brand_name} iPad line offers excellent options.",
            f"For wireless earbuds, {brand_name} AirPods provide good sound quality."
        ],
        "Microsoft": [
            f"For business productivity, {brand_name} Office 365 is widely used.",
            f"When choosing cloud platforms, {brand_name} Azure provides robust solutions.",
            f"Many developers appreciate {brand_name} Visual Studio for development.",
            f"If you need an operating system for business use, {brand_name} Windows is popular.",
            f"For gaming, the {brand_name} Xbox series offers excellent performance."
        ]
    }
    
    sample_prompts = [
        f"What are the best alternatives to {brand_name}?",
        f"How does {brand_name} compare to its competitors?",
        f"Is {brand_name} worth the investment?",
        f"Can you recommend something like {brand_name}?",
        f"Tell me about {brand_name}'s latest features"
    ]
    
    mentions_text = sample_mentions.get(brand_name, sample_mentions["Tesla"])
    
    db = SessionLocal()
    try:
        for i in range(count):
            # Random timestamp within last 24 hours
            time_ago = timedelta(hours=random.randint(0, 24), minutes=random.randint(0, 59))
            timestamp = datetime.utcnow() - time_ago
            
            mention = BrandMention(
                brand_name=brand_name,
                mention_text=random.choice(mentions_text),
                platform=random.choice(platforms),
                timestamp=timestamp,
                triggering_prompt=random.choice(sample_prompts),
                sentiment_score=random.choice(["positive", "neutral", "negative"]),
                is_processed=True
            )
            
            db.add(mention)
        
        db.commit()
        return True
        
    except Exception as e:
        print(f"Error generating demo data: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def clear_all_mentions() -> bool:
    """Clear all mentions from database"""
    db = SessionLocal()
    try:
        count = db.query(BrandMention).count()
        db.query(BrandMention).delete()
        db.commit()
        print(f"Cleared {count} mentions from database")
        return True
    except Exception as e:
        print(f"Error clearing data: {e}")
        db.rollback()
        return False
    finally:
        db.close()