#!/usr/bin/env python3
"""
Startup script for AI Brand Mention Tracker
"""
import subprocess
import sys
import os
from pathlib import Path

def check_requirements():
    """Check if requirements are installed"""
    try:
        import fastapi
        import uvicorn
        import sqlalchemy
        import openai
        return True
    except ImportError:
        return False

def install_requirements():
    """Install requirements from requirements.txt"""
    print("Installing required packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("✅ Requirements installed successfully!")

def setup_environment():
    """Setup environment file if it doesn't exist"""
    env_file = Path(".env")
    example_file = Path(".env.example")
    
    if not env_file.exists() and example_file.exists():
        print("Creating .env file from template...")
        with open(example_file, 'r') as f:
            content = f.read()
        
        with open(env_file, 'w') as f:
            f.write(content)
        
        print("⚠️  Please edit .env file and add your OpenAI API key!")
        print("   The app will work without it, but with limited AI-generated content.")
        return True
    return False

def initialize_database():
    """Initialize the database"""
    print("Initializing database...")
    from app.models.database import init_database
    init_database()
    print("✅ Database initialized!")

def main():
    """Main startup function"""
    print("🔍 AI Brand Mention Tracker - Startup")
    print("=" * 50)
    
    # Check if requirements are installed
    if not check_requirements():
        print("Installing requirements...")
        install_requirements()
    
    # Setup environment
    env_created = setup_environment()
    
    # Initialize database
    initialize_database()
    
    print("\n🚀 Starting the application...")
    print("Dashboard will be available at: http://localhost:8000")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    if env_created:
        print("\n💡 Don't forget to add your OpenAI API key to .env file for enhanced features!")
    
    # Start the server
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()