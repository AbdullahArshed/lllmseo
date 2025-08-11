"""
AI Brand Mention Tracker - Modular Main Application
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import logging
from pathlib import Path

# Import modular components
from app.core.config import settings
from app.core.websocket import manager
from app.api import monitoring, mentions, stats
from app.models.database import init_database

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    debug=settings.debug
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="app/templates")

# Include API routers
app.include_router(monitoring.router, prefix=settings.api_prefix)
app.include_router(mentions.router, prefix=settings.api_prefix)
app.include_router(stats.router, prefix=settings.api_prefix)

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Initialize database
    init_database()
    logger.info("Database initialized")
    
    # Log configuration
    logger.info(f"Monitoring {len(settings.monitored_platforms)} platforms")
    logger.info(f"Check interval: {settings.monitoring_interval} seconds")
    
    if settings.openai_api_key:
        logger.info("OpenAI integration enabled")
    else:
        logger.warning("OpenAI API key not configured - using fallback mentions")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down application")
    
    # Stop monitoring if active
    from app.services.monitoring import monitor
    if monitor.is_monitoring:
        await monitor.stop_monitoring()
        logger.info("Monitoring stopped")

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """Serve the main dashboard"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from app.services.monitoring import monitor
    return {
        "status": "healthy",
        "version": settings.app_version,
        "monitoring_active": monitor.is_monitoring,
        "current_brand": monitor.current_brand,
        "platforms_count": len(settings.monitored_platforms),
        "websocket_connections": manager.get_connection_count()
    }

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    connected = await manager.connect(websocket)
    if not connected:
        return
    
    try:
        # Send initial connection message
        await manager.send_personal_message({
            "type": "connected",
            "data": {
                "message": "Connected to AI Brand Mention Tracker",
                "platforms": settings.monitored_platforms
            }
        }, websocket)
        
        # Keep connection alive and handle client messages
        while True:
            try:
                data = await websocket.receive_text()
                # Handle client messages if needed (ping/pong, etc.)
                import json
                try:
                    message = json.loads(data)
                    if message.get("type") == "pong":
                        logger.debug("Received pong from client")
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received from client: {data}")
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)

# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors"""
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request}, 
        status_code=404
    )

@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {exc}")
    return {
        "error": "Internal server error",
        "message": "Something went wrong. Please try again later."
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {settings.host}:{settings.port}")
    uvicorn.run(
        "main_modular:app", 
        host=settings.host, 
        port=settings.port, 
        reload=settings.debug,
        log_level="info"
    )