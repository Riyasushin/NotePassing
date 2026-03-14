"""WebSocket connection manager for handling real-time connections."""
from typing import Dict, Optional
from datetime import datetime

from fastapi import WebSocket

from app.utils.uuid_utils import generate_uuid


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        # Map device_id to WebSocket connection
        self.active_connections: Dict[str, WebSocket] = {}
        # Map device_id to connection_id for tracking
        self.connection_ids: Dict[str, str] = {}
    
    async def connect(self, device_id: str, websocket: WebSocket) -> str:
        """
        Accept a WebSocket connection and register it.
        
        Args:
            device_id: Device ID
            websocket: WebSocket connection
        
        Returns:
            Connection ID
        """
        await websocket.accept()
        
        # Generate connection ID
        connection_id = generate_uuid()
        
        # Close existing connection if any (reconnect scenario)
        if device_id in self.active_connections:
            old_ws = self.active_connections[device_id]
            try:
                await old_ws.close()
            except Exception:
                pass
        
        # Register new connection
        self.active_connections[device_id] = websocket
        self.connection_ids[device_id] = connection_id
        
        # Send connection confirmation
        await self.send_personal_message(
            device_id,
            {
                "type": "connected",
                "payload": {
                    "device_id": device_id,
                    "server_time": datetime.utcnow().isoformat() + "Z",
                },
            }
        )
        
        return connection_id
    
    def disconnect(self, device_id: str) -> None:
        """
        Disconnect a WebSocket connection.
        
        Args:
            device_id: Device ID to disconnect
        """
        if device_id in self.active_connections:
            del self.active_connections[device_id]
        if device_id in self.connection_ids:
            del self.connection_ids[device_id]
    
    async def send_personal_message(self, device_id: str, message: dict) -> bool:
        """
        Send a message to a specific device.
        
        Args:
            device_id: Target device ID
            message: Message to send
        
        Returns:
            True if sent successfully, False otherwise
        """
        if device_id not in self.active_connections:
            return False
        
        websocket = self.active_connections[device_id]
        try:
            await websocket.send_json(message)
            return True
        except Exception:
            # Connection might be closed
            self.disconnect(device_id)
            return False
    
    async def broadcast(self, message: dict, exclude: Optional[str] = None) -> None:
        """
        Broadcast a message to all connected devices.
        
        Args:
            message: Message to broadcast
            exclude: Device ID to exclude from broadcast
        """
        disconnected = []
        
        for device_id, websocket in self.active_connections.items():
            if exclude and device_id == exclude:
                continue
            
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(device_id)
        
        # Clean up disconnected
        for device_id in disconnected:
            self.disconnect(device_id)
    
    def is_connected(self, device_id: str) -> bool:
        """
        Check if a device is connected.
        
        Args:
            device_id: Device ID to check
        
        Returns:
            True if connected, False otherwise
        """
        return device_id in self.active_connections
    
    def get_connection_id(self, device_id: str) -> Optional[str]:
        """
        Get connection ID for a device.
        
        Args:
            device_id: Device ID
        
        Returns:
            Connection ID or None
        """
        return self.connection_ids.get(device_id)


# Global connection manager instance
manager = ConnectionManager()


# Helper functions for pushing events to clients

async def push_new_message(receiver_id: str, message_data: dict) -> bool:
    """Push new message notification to receiver."""
    return await manager.send_personal_message(
        receiver_id,
        {
            "type": "new_message",
            "payload": message_data,
        }
    )


async def push_message_sent(sender_id: str, message_data: dict) -> bool:
    """Push message sent confirmation to sender."""
    return await manager.send_personal_message(
        sender_id,
        {
            "type": "message_sent",
            "payload": message_data,
        }
    )


async def push_friend_request(receiver_id: str, request_data: dict) -> bool:
    """Push friend request notification to receiver."""
    return await manager.send_personal_message(
        receiver_id,
        {
            "type": "friend_request",
            "payload": request_data,
        }
    )


async def push_friend_response(receiver_id: str, response_data: dict) -> bool:
    """Push friend request response to sender."""
    return await manager.send_personal_message(
        receiver_id,
        {
            "type": "friend_response",
            "payload": response_data,
        }
    )


async def push_friend_deleted(receiver_id: str, deleted_data: dict) -> bool:
    """Push friendship removal notification to the other side."""
    return await manager.send_personal_message(
        receiver_id,
        {
            "type": "friend_deleted",
            "payload": deleted_data,
        }
    )


async def push_boost(receiver_id: str, boost_data: dict) -> bool:
    """Push boost notification to receiver."""
    return await manager.send_personal_message(
        receiver_id,
        {
            "type": "boost",
            "payload": boost_data,
        }
    )


async def push_session_expired(device_ids: list, session_data: dict) -> None:
    """Push session expired notification to devices."""
    message = {
        "type": "session_expired",
        "payload": session_data,
    }
    
    for device_id in device_ids:
        await manager.send_personal_message(device_id, message)


async def push_messages_read(sender_id: str, read_data: dict) -> bool:
    """Push messages read notification to sender."""
    return await manager.send_personal_message(
        sender_id,
        {
            "type": "messages_read",
            "payload": read_data,
        }
    )


async def push_error(device_id: str, error_code: int, error_message: str) -> bool:
    """Push error notification to device."""
    return await manager.send_personal_message(
        device_id,
        {
            "type": "error",
            "payload": {
                "code": error_code,
                "message": error_message,
            },
        }
    )
