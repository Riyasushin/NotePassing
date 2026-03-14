"""Tests for WebSocket functionality."""
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.websocket_manager import (
    ConnectionManager,
    manager,
    push_new_message,
    push_message_sent,
    push_friend_request,
    push_error,
)
from app.services.device_service import DeviceService
from app.schemas.device import DeviceInitRequest
from app.utils.uuid_utils import generate_device_id


class TestConnectionManager:
    """Test ConnectionManager class."""
    
    @pytest.mark.asyncio
    async def test_connection_manager_connect_disconnect(self):
        """Test connection manager connect and disconnect."""
        # Create a mock WebSocket
        class MockWebSocket:
            def __init__(self):
                self.accepted = False
                self.sent_messages = []
                self.closed = False
            
            async def accept(self):
                self.accepted = True
            
            async def send_json(self, data):
                self.sent_messages.append(data)
            
            async def close(self, code=None, reason=None):
                self.closed = True
        
        ws = MockWebSocket()
        device_id = generate_device_id()
        
        # Test connect
        connection_id = await manager.connect(device_id, ws)
        
        assert ws.accepted is True
        assert connection_id is not None
        assert manager.is_connected(device_id) is True
        assert manager.get_connection_id(device_id) == connection_id
        
        # Check connected message was sent
        assert len(ws.sent_messages) == 1
        assert ws.sent_messages[0]["type"] == "connected"
        
        # Test disconnect
        manager.disconnect(device_id)
        assert manager.is_connected(device_id) is False
    
    @pytest.mark.asyncio
    async def test_send_personal_message(self):
        """Test sending personal message."""
        class MockWebSocket:
            def __init__(self):
                self.sent_messages = []
            
            async def accept(self):
                pass
            
            async def send_json(self, data):
                self.sent_messages.append(data)
        
        ws = MockWebSocket()
        device_id = generate_device_id()
        
        await manager.connect(device_id, ws)
        
        # Send message
        result = await manager.send_personal_message(
            device_id,
            {"type": "test", "payload": {"data": "hello"}}
        )
        
        assert result is True
        assert len(ws.sent_messages) == 2  # connected + test
        assert ws.sent_messages[1]["type"] == "test"
    
    @pytest.mark.asyncio
    async def test_send_to_disconnected_device(self):
        """Test sending message to disconnected device."""
        device_id = generate_device_id()
        
        result = await manager.send_personal_message(
            device_id,
            {"type": "test"}
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_reconnect_replaces_old_connection(self):
        """Test that reconnect replaces old connection."""
        class MockWebSocket:
            def __init__(self, name):
                self.name = name
                self.closed = False
                self.sent_messages = []
            
            async def accept(self):
                pass
            
            async def send_json(self, data):
                self.sent_messages.append(data)
            
            async def close(self):
                self.closed = True
        
        device_id = generate_device_id()
        ws1 = MockWebSocket("ws1")
        ws2 = MockWebSocket("ws2")
        
        # First connection
        await manager.connect(device_id, ws1)
        assert manager.is_connected(device_id) is True
        
        # Second connection (should replace first)
        await manager.connect(device_id, ws2)
        assert manager.is_connected(device_id) is True
        assert ws1.closed is True


class TestWebSocketPushFunctions:
    """Test WebSocket push helper functions."""
    
    @pytest.mark.asyncio
    async def test_push_new_message(self):
        """Test push_new_message function."""
        class MockWebSocket:
            def __init__(self):
                self.sent_messages = []
            
            async def accept(self):
                pass
            
            async def send_json(self, data):
                self.sent_messages.append(data)
        
        ws = MockWebSocket()
        device_id = generate_device_id()
        
        await manager.connect(device_id, ws)
        
        result = await push_new_message(
            device_id,
            {
                "message_id": "msg-123",
                "content": "Hello",
            }
        )
        
        assert result is True
        # Find the new_message type
        new_msg = next((m for m in ws.sent_messages if m.get("type") == "new_message"), None)
        assert new_msg is not None
        assert new_msg["payload"]["message_id"] == "msg-123"
    
    @pytest.mark.asyncio
    async def test_push_message_sent(self):
        """Test push_message_sent function."""
        class MockWebSocket:
            def __init__(self):
                self.sent_messages = []
            
            async def accept(self):
                pass
            
            async def send_json(self, data):
                self.sent_messages.append(data)
        
        ws = MockWebSocket()
        device_id = generate_device_id()
        
        await manager.connect(device_id, ws)
        
        result = await push_message_sent(
            device_id,
            {"message_id": "msg-456"}
        )
        
        assert result is True
        sent_msg = next((m for m in ws.sent_messages if m.get("type") == "message_sent"), None)
        assert sent_msg is not None
    
    @pytest.mark.asyncio
    async def test_push_friend_request(self):
        """Test push_friend_request function."""
        class MockWebSocket:
            def __init__(self):
                self.sent_messages = []
            
            async def accept(self):
                pass
            
            async def send_json(self, data):
                self.sent_messages.append(data)
        
        ws = MockWebSocket()
        device_id = generate_device_id()
        
        await manager.connect(device_id, ws)
        
        result = await push_friend_request(
            device_id,
            {"request_id": "req-789", "sender": {"nickname": "User"}}
        )
        
        assert result is True
        friend_req = next((m for m in ws.sent_messages if m.get("type") == "friend_request"), None)
        assert friend_req is not None
    
    @pytest.mark.asyncio
    async def test_push_error(self):
        """Test push_error function."""
        class MockWebSocket:
            def __init__(self):
                self.sent_messages = []
            
            async def accept(self):
                pass
            
            async def send_json(self, data):
                self.sent_messages.append(data)
        
        ws = MockWebSocket()
        device_id = generate_device_id()
        
        await manager.connect(device_id, ws)
        
        result = await push_error(device_id, 4001, "Test error")
        
        assert result is True
        error_msg = next((m for m in ws.sent_messages if m.get("type") == "error"), None)
        assert error_msg is not None
        assert error_msg["payload"]["code"] == 4001
        assert error_msg["payload"]["message"] == "Test error"


class TestWebSocketIntegration:
    """Integration tests for WebSocket."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, client: AsyncClient):
        """Test WebSocket connection endpoint."""
        device_id = generate_device_id()
        
        # Create device
        await client.post("/api/v1/device/init", json={
            "device_id": device_id,
            "nickname": "Test User",
        })
        
        # Note: Testing WebSocket with httpx AsyncClient requires special handling
        # This is a simplified test - full WebSocket testing would use websockets library
        
        # For now, just verify the endpoint exists by checking connection is rejected
        # for invalid device_id
        response = await client.get("/api/v1/ws?device_id=invalid")
        # Should return error (not 200 since it's WebSocket)
        assert response.status_code != 200


# Cleanup after tests
@pytest.fixture(autouse=True)
def cleanup_manager():
    """Clean up connection manager after each test."""
    yield
    # Clear all connections
    manager.active_connections.clear()
    manager.connection_ids.clear()
