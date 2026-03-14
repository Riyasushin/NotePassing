"""
消息API集成测试 - 测试Message Router的实际端点
"""

import pytest
from unittest.mock import patch, AsyncMock


class TestMessagingAPI:
    """消息API测试类"""
    
    @pytest.mark.asyncio
    async def test_send_message_endpoint(self, async_client):
        """P0: 测试POST /messages端点"""
        with patch("app.routers.message.MessagingService") as MockService, \
             patch("app.routers.message.ws_manager") as mock_ws:
            
            mock_service = AsyncMock()
            mock_service.send_message.return_value = {
                "message_id": "msg-123",
                "session_id": "sess-123",
                "status": "sent",
                "created_at": "2026-03-14T10:53:00Z"
            }
            MockService.return_value = mock_service
            mock_ws.send_new_message = AsyncMock()
            mock_ws.send_message_sent = AsyncMock()
            
            response = await async_client.post("/api/v1/messages", json={
                "sender_id": "550e8400-e29b-41d4-a716-446655440001",
                "receiver_id": "550e8400-e29b-41d4-a716-446655440002",
                "content": "你好",
                "type": "common"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["status"] == "sent"
    
    @pytest.mark.asyncio
    async def test_send_message_blocked(self, async_client):
        """P0: 测试发送消息给屏蔽者返回4004错误"""
        with patch("app.routers.message.MessagingService") as MockService:
            from app.exceptions import BlockedError
            
            mock_service = AsyncMock()
            mock_service.send_message.side_effect = BlockedError()
            MockService.return_value = mock_service
            
            response = await async_client.post("/api/v1/messages", json={
                "sender_id": "550e8400-e29b-41d4-a716-446655440001",
                "receiver_id": "550e8400-e29b-41d4-a716-446655440002",
                "content": "你好"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 4004
    
    @pytest.mark.asyncio
    async def test_send_message_temp_limit(self, async_client):
        """P0: 测试陌生人消息限制返回4001错误"""
        with patch("app.routers.message.MessagingService") as MockService:
            from app.exceptions import TempMessageLimitError
            
            mock_service = AsyncMock()
            mock_service.send_message.side_effect = TempMessageLimitError()
            MockService.return_value = mock_service
            
            response = await async_client.post("/api/v1/messages", json={
                "sender_id": "550e8400-e29b-41d4-a716-446655440001",
                "receiver_id": "550e8400-e29b-41d4-a716-446655440002",
                "content": "第三条消息"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 4001
    
    @pytest.mark.asyncio
    async def test_get_messages_endpoint(self, async_client):
        """P0: 测试GET /messages/{session_id}端点"""
        with patch("app.routers.message.MessagingService") as MockService:
            mock_service = AsyncMock()
            mock_service.get_message_history.return_value = {
                "session_id": "sess-123",
                "messages": [
                    {
                        "message_id": "msg-1",
                        "sender_id": "550e8400-e29b-41d4-a716-446655440001",
                        "content": "你好",
                        "type": "common",
                        "status": "read",
                        "created_at": "2026-03-14T10:53:00Z"
                    }
                ],
                "has_more": False
            }
            MockService.return_value = mock_service
            
            response = await async_client.get(
                "/api/v1/messages/sess-123",
                params={"device_id": "550e8400-e29b-41d4-a716-446655440001"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert len(data["data"]["messages"]) == 1
    
    @pytest.mark.asyncio
    async def test_mark_read_endpoint(self, async_client):
        """P0: 测试POST /messages/read端点"""
        with patch("app.routers.message.MessagingService") as MockService, \
             patch("app.routers.message.ws_manager") as mock_ws:
            
            mock_service = AsyncMock()
            mock_service.mark_messages_read.return_value = {
                "updated_count": 2,
                "sender_ids": ["550e8400-e29b-41d4-a716-446655440001"]
            }
            MockService.return_value = mock_service
            mock_ws.send_messages_read = AsyncMock()
            
            response = await async_client.post("/api/v1/messages/read", json={
                "device_id": "550e8400-e29b-41d4-a716-446655440002",
                "message_ids": ["msg-1", "msg-2"]
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["updated_count"] == 2
