"""
好友关系API集成测试 - 测试Friendship Router的实际端点
"""

import pytest
from unittest.mock import patch, AsyncMock


class TestFriendshipAPI:
    """好友关系API测试类"""
    
    @pytest.mark.asyncio
    async def test_get_friends_endpoint(self, async_client):
        """P0: 测试GET /friends端点"""
        with patch("app.routers.friendship.RelationService") as MockService:
            mock_service = AsyncMock()
            mock_service.get_friends_list.return_value = [
                {
                    "device_id": "550e8400-e29b-41d4-a716-446655440002",
                    "nickname": "好友A",
                    "avatar": "avatar.jpg",
                    "tags": ["摄影"],
                    "profile": "简介",
                    "is_anonymous": False,
                    "last_chat_at": "2026-03-14T11:00:00Z"
                }
            ]
            MockService.return_value = mock_service
            
            response = await async_client.get(
                "/api/v1/friends",
                params={"device_id": "550e8400-e29b-41d4-a716-446655440001"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert len(data["data"]["friends"]) == 1
    
    @pytest.mark.asyncio
    async def test_send_friend_request_endpoint(self, async_client):
        """P0: 测试POST /friends/request端点"""
        with patch("app.routers.friendship.RelationService") as MockService, \
             patch("app.routers.friendship.ws_manager") as mock_ws:
            
            mock_service = AsyncMock()
            mock_service.send_friend_request.return_value = {
                "request_id": "req-123",
                "status": "pending",
                "created_at": "2026-03-14T10:53:00Z"
            }
            mock_service._get_device_info.return_value = {
                "device_id": "550e8400-e29b-41d4-a716-446655440001",
                "nickname": "发送者"
            }
            MockService.return_value = mock_service
            mock_ws.send_friend_request = AsyncMock()
            
            response = await async_client.post("/api/v1/friends/request", json={
                "sender_id": "550e8400-e29b-41d4-a716-446655440001",
                "receiver_id": "550e8400-e29b-41d4-a716-446655440002",
                "message": "想加你为好友"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_send_friend_request_cooldown(self, async_client):
        """P0: 测试好友申请冷却期返回4005错误"""
        with patch("app.routers.friendship.RelationService") as MockService:
            from app.exceptions import CooldownError
            
            mock_service = AsyncMock()
            mock_service.send_friend_request.side_effect = CooldownError()
            MockService.return_value = mock_service
            
            response = await async_client.post("/api/v1/friends/request", json={
                "sender_id": "550e8400-e29b-41d4-a716-446655440001",
                "receiver_id": "550e8400-e29b-41d4-a716-446655440002"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 4005
    
    @pytest.mark.asyncio
    async def test_respond_friend_request_accept(self, async_client):
        """P0: 测试PUT /friends/{request_id}接受申请"""
        with patch("app.routers.friendship.RelationService") as MockService, \
             patch("app.routers.friendship.ws_manager") as mock_ws:
            
            mock_service = AsyncMock()
            mock_service.respond_friend_request.return_value = {
                "request_id": "req-123",
                "status": "accepted",
                "friend": {
                    "device_id": "550e8400-e29b-41d4-a716-446655440001",
                    "nickname": "新好友"
                },
                "session_id": "perm-sess-123"
            }
            MockService.return_value = mock_service
            mock_ws.send_friend_response = AsyncMock()
            
            response = await async_client.put("/api/v1/friends/req-123", json={
                "device_id": "550e8400-e29b-41d4-a716-446655440002",
                "action": "accept"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert data["data"]["status"] == "accepted"
    
    @pytest.mark.asyncio
    async def test_block_user_endpoint(self, async_client):
        """P0: 测试POST /block端点"""
        with patch("app.routers.friendship.RelationService") as MockService:
            mock_service = AsyncMock()
            MockService.return_value = mock_service
            
            response = await async_client.post("/api/v1/block", json={
                "device_id": "550e8400-e29b-41d4-a716-446655440001",
                "target_id": "550e8400-e29b-41d4-a716-446655440002"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
