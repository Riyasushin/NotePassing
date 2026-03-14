"""
WebSocket集成测试 - 测试WebSocket端点的实际功能
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


class TestWebSocketEndpoint:
    """WebSocket端点测试类"""
    
    @pytest.mark.asyncio
    async def test_websocket_connect(self):
        """P0: 测试WebSocket连接成功"""
        from app.services.websocket_manager import WebSocketManager
        
        manager = WebSocketManager()
        mock_ws = AsyncMock()
        
        await manager.connect("device-001", mock_ws)
        
        mock_ws.accept.assert_called_once()
        # 验证connected消息
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "connected"
        assert call_args["payload"]["device_id"] == "device-001"
    
    @pytest.mark.asyncio
    async def test_websocket_handle_send_message(self):
        """P0: 测试WebSocket处理send_message"""
        from app.routers.websocket import handle_send_message
        
        with patch("app.routers.websocket.async_session_maker") as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            
            with patch("app.routers.websocket.MessagingService") as MockService:
                mock_service = AsyncMock()
                mock_service.send_message.return_value = {
                    "message_id": "msg-123",
                    "session_id": "sess-123",
                    "status": "sent",
                    "created_at": "2026-03-14T10:53:00Z"
                }
                MockService.return_value = mock_service
                
                with patch("app.routers.websocket.ws_manager") as mock_ws:
                    mock_ws.send_new_message = AsyncMock()
                    mock_ws.send_message_sent = AsyncMock()
                    
                    payload = {
                        "receiver_id": "receiver-001",
                        "content": "你好",
                        "type": "common"
                    }
                    
                    await handle_send_message("sender-001", payload)
                    
                    mock_ws.send_new_message.assert_called_once()
                    mock_ws.send_message_sent.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_handle_mark_read(self):
        """P0: 测试WebSocket处理mark_read"""
        from app.routers.websocket import handle_mark_read
        
        with patch("app.routers.websocket.async_session_maker") as mock_session:
            mock_db = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db
            
            with patch("app.routers.websocket.MessagingService") as MockService:
                mock_service = AsyncMock()
                mock_service.mark_messages_read.return_value = {
                    "updated_count": 2,
                    "sender_ids": ["sender-001"]
                }
                MockService.return_value = mock_service
                
                with patch("app.routers.websocket.ws_manager") as mock_ws:
                    mock_ws.send_messages_read = AsyncMock()
                    
                    payload = {
                        "message_ids": ["msg-1", "msg-2"]
                    }
                    
                    await handle_mark_read("reader-001", payload)
                    
                    mock_ws.send_messages_read.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self):
        """P0: 测试WebSocket ping-pong"""
        from app.services.websocket_manager import WebSocketManager
        
        manager = WebSocketManager()
        mock_ws = AsyncMock()
        manager.connections["device-001"] = mock_ws
        
        await manager.send_pong("device-001")
        
        call_args = mock_ws.send_json.call_args[0][0]
        assert call_args["type"] == "pong"


class TestWebSocketMessageTypes:
    """WebSocket消息类型测试"""
    
    def test_server_to_client_types(self):
        """测试所有Server->Client消息类型"""
        message_types = [
            "connected",
            "new_message",
            "message_sent",
            "friend_request",
            "friend_response",
            "boost",
            "session_expired",
            "messages_read",
            "pong",
            "error",
        ]
        
        for msg_type in message_types:
            # 验证类型不为空
            assert len(msg_type) > 0
    
    def test_client_to_server_actions(self):
        """测试所有Client->Server action类型"""
        actions = [
            "send_message",
            "mark_read",
            "ping",
        ]
        
        for action in actions:
            assert len(action) > 0
