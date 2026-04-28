"""
Real-time WebSocket Gateway — Phase 15, Task 15.1

Handles real-time alert broadcasts to connected operators.
"""

import json
import logging
from typing import Dict, List, Set
from uuid import UUID

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user_optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts.
    """
    def __init__(self):
        # active_connections[user_id] = [WebSocket, ...]
        self.active_connections: Dict[UUID, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: UUID):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info("User %s connected to alert gateway. Total active users: %d", 
                    user_id, len(self.active_connections))

    def disconnect(self, websocket: WebSocket, user_id: UUID):
        if user_id in self.active_connections:
            if websocket in self.active_connections[user_id]:
                self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info("User %s disconnected. Active users: %d", user_id, len(self.active_connections))

    async def broadcast(self, message: dict):
        """Broadcast alert to all connected operators."""
        payload = json.dumps(message)
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_text(payload)
                except Exception as e:
                    logger.error("Failed to send broadcast to user %s: %s", user_id, e)

manager = ConnectionManager()
router = APIRouter(prefix="/ws", tags=["Real-time Gateway"])

@router.websocket("/alerts")
async def alert_websocket_endpoint(
    websocket: WebSocket,
    token: str = None # Passed as query param: ws://.../ws/alerts?token=xyz
):
    """
    WebSocket endpoint for real-time alert notifications.
    """
    from app.core.security import decode_token
    from jose import JWTError
    
    user_id = None
    
    # 1. Authenticate via token in query param
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
        
    try:
        payload = decode_token(token)
        user_id_str = payload.get("sub")
        if not user_id_str:
             await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
             return
        user_id = UUID(user_id_str)
    except (JWTError, ValueError):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # 2. Accept connection
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Keep connection alive and wait for client messages if needed
            # For now, we only push from server -> client
            data = await websocket.receive_text()
            # Handle heartbeat or client commands
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error("WebSocket error for user %s: %s", user_id, e)
        manager.disconnect(websocket, user_id)
