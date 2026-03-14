"""
WebSocket管理器单元测试 - 测试WebSocketManager的实际实现
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.websocket_manager import WebSocketManager


class TestWebSocketManager:
    """WebSocketManager测试类"""
    
    @pytest.fixture
    def manager(self):
        """创建管理器实例"""
        return WebSocketManager()
    
    @pytest.fixture
    def mock_websocket(self):
        """Mock WebSocket"""
        ws = AsyncMock()
        return ws
    
    @pytest.mark.asyncio
    async def test_connect_success(self, manager, mock_websocket):
        """P0: 测试WebSocket连接成功"""
        device_id = "550e8400-e29b-41d4-a716-446655440001"
        
        await manager.connect(device_id, mock_websocket)
        
        # 应接受连接并发送connected消息
        mock_websocket.accept.assert_called_once()
        mock_websocket.send_json.assert_called_once()
        
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "connected"
        assert call_args["payload"]["device_id"] == device_id
    
    def test_disconnect(self, manager, mock_websocket):
        """P0: 测试断开连接清理"""
        device_id = "550e8400-e29b-41d4-a716-446655440001"
        
        # 先连接
        manager.connections[device_id] = mock_websocket
        
        # 断开
        manager.disconnect(device_id)
        
        assert device_id not in manager.connections
    
    @pytest.mark.asyncio
    async def test_send_message_to_connected(self, manager, mock_websocket):
        """P0: 测试向已连接客户端发送消息"""
        device_id = "550e8400-e29b-41d4-a716-446655440001"
        manager.connections[device_id] = mock_websocket
        
        message = {"type": "new_message", "payload": {"content": "Hello"}}
        
        result = await manager.send_message(device_id, message)
        
        assert result is True
        mock_websocket.send_json.assert_called_with(message)
    
    @pytest.mark.asyncio
    async def test_send_message_to_disconnected(self, manager):
        """P1: 测试向未连接客户端发送消息"""
        device_id = "550e8400-e29b-41d4-a716-446655440001"
        
        message = {"type": "new_message", "payload": {}}
        
        result = await manager.send_message(device_id, message)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_new_message(self, manager, mock_websocket):
        """P0: 测试推送新消息"""
        device_id = "550e8400-e29b-41d4-a716-446655440001"
        manager.connections[device_id] = mock_websocket
        
        await manager.send_new_message(
            device_id=device_id,
            message_id="msg-123",
            sender_id="sender-001",
            session_id="sess-123",
            content="你好",
            msg_type="common",
            created_at="2026-03-14T10:53:00Z"
        )
        
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "new_message"
        assert call_args["payload"]["content"] == "你好"
    
    @pytest.mark.asyncio
    async def test_send_boost(self, manager, mock_websocket):
        """P0: 测试推送Boost通知"""
        device_id = "550e8400-e29b-41d4-a716-446655440001"
        manager.connections[device_id] = mock_websocket
        
        await manager.send_boost(
            device_id=device_id,
            friend_id="friend-001",
            nickname="好友",
            distance=2.5
        )
        
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "boost"
        assert call_args["payload"]["nickname"] == "好友"
        assert call_args["payload"]["distance_estimate"] == 2.5
    
    @pytest.mark.asyncio
    async def test_send_pong(self, manager, mock_websocket):
        """P0: 测试发送心跳响应"""
        device_id = "550e8400-e29b-41d4-a716-446655440001"
        manager.connections[device_id] = mock_websocket
        
        await manager.send_pong(device_id)
        
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "pong"
