"""WebSocket manager for real-time dashboard updates."""

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from collections import defaultdict

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect


@dataclass
class WebSocketMessage:
    type: str
    data: dict
    timestamp: str = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_json(self) -> str:
        return json.dumps({"type": self.type, "data": self.data, "timestamp": self.timestamp})


class WebSocketManager:
    """Manager for WebSocket connections and real-time updates."""

    def __init__(self):
        # Store connections by channel/topic
        self.connections: dict[str, list[WebSocket]] = defaultdict(list)
        # Track which connections are subscribed to which channels
        self.connection_channels: dict[WebSocket, set[str]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, channel: str = "default"):
        """Accept a WebSocket connection and subscribe to a channel."""
        await websocket.accept()
        self.connections[channel].append(websocket)
        self.connection_channels[websocket].add(channel)

        # Send welcome message
        await self.send_personal_message(
            websocket,
            WebSocketMessage(
                type="connected",
                data={"channel": channel, "message": "Successfully connected to real-time updates"},
            ),
        )

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection from all channels."""
        channels = self.connection_channels.get(websocket, set())
        for channel in channels:
            if websocket in self.connections[channel]:
                self.connections[channel].remove(websocket)
        del self.connection_channels[websocket]

    async def send_personal_message(self, websocket: WebSocket, message: WebSocketMessage):
        """Send a message to a specific connection."""
        try:
            await websocket.send_text(message.to_json())
        except Exception as e:
            print(f"Error sending personal message: {e}")
            self.disconnect(websocket)

    async def broadcast(self, channel: str, message: WebSocketMessage):
        """Broadcast a message to all connections in a channel."""
        disconnected = []
        for connection in self.connections[channel]:
            try:
                await connection.send_text(message.to_json())
            except Exception as e:
                print(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)

        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_agent_status(self, agent_id: str, status: str, data: dict = None):
        """Broadcast agent status update."""
        await self.broadcast(
            "agents",
            WebSocketMessage(
                type="agent_status",
                data={"agent_id": agent_id, "status": status, **(data or {})},
            ),
        )

    async def broadcast_job_update(self, job_id: str, status: str, data: dict = None):
        """Broadcast job status update."""
        await self.broadcast(
            "jobs",
            WebSocketMessage(
                type="job_update",
                data={"job_id": job_id, "status": status, **(data or {})},
            ),
        )

    async def broadcast_opportunity_found(self, opportunity: dict):
        """Broadcast new opportunity discovery."""
        await self.broadcast(
            "opportunities",
            WebSocketMessage(
                type="opportunity_found",
                data=opportunity,
            ),
        )

    async def broadcast_verification_complete(self, verification: dict):
        """Broadcast verification completion."""
        await self.broadcast(
            "verifications",
            WebSocketMessage(
                type="verification_complete",
                data=verification,
            ),
        )

    async def broadcast_alert(self, alert: dict):
        """Broadcast alert."""
        await self.broadcast(
            "alerts",
            WebSocketMessage(
                type="alert",
                data=alert,
            ),
        )

    async def broadcast_metrics(self, metrics: dict):
        """Broadcast system metrics."""
        await self.broadcast(
            "metrics",
            WebSocketMessage(
                type="metrics",
                data=metrics,
            ),
        )

    def get_connection_count(self, channel: str = None) -> int:
        """Get the number of active connections."""
        if channel:
            return len(self.connections[channel])
        return sum(len(conns) for conns in self.connections.values())


# Global instance
_websocket_manager: Optional[WebSocketManager] = None


def get_websocket_manager() -> WebSocketManager:
    """Get or create the global WebSocket manager instance."""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager
