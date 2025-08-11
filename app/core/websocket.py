"""
WebSocket connection manager for real-time updates
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import json
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manages WebSocket connections and broadcasting"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.max_connections = 100
    
    async def connect(self, websocket: WebSocket) -> bool:
        """Accept a new WebSocket connection"""
        if len(self.active_connections) >= self.max_connections:
            await websocket.close(code=1000, reason="Too many connections")
            return False
        
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")
        return True
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific WebSocket connection"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        message_str = json.dumps(message)
        disconnected = []
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.disconnect(conn)
    
    async def broadcast_mention(self, mention_data: dict):
        """Broadcast a new mention to all clients"""
        message = {
            "type": "mention",
            "data": mention_data
        }
        await self.broadcast(message)
    
    async def broadcast_status(self, status: bool, brand: str = None):
        """Broadcast monitoring status change"""
        message = {
            "type": "status",
            "data": {
                "is_active": status,
                "brand": brand
            }
        }
        await self.broadcast(message)
    
    async def broadcast_error(self, error_message: str):
        """Broadcast error message to all clients"""
        message = {
            "type": "error",
            "data": {
                "message": error_message
            }
        }
        await self.broadcast(message)
    
    def get_connection_count(self) -> int:
        """Get current number of active connections"""
        return len(self.active_connections)
    
    async def ping_all(self):
        """Send ping to all connections to check health"""
        message = {
            "type": "ping",
            "data": {}
        }
        await self.broadcast(message)

# Global connection manager instance
manager = ConnectionManager()