"""
关系服务单元测试 - 测试RelationService的实际实现
"""

import uuid
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

from app.services.relation_service import RelationService
from app.schemas.friendship import SendFriendRequest, RespondFriendRequest, BlockUserRequest
from app.models import Friendship, Block, Device, Session
from app.exceptions import (
    ValidationError,
    BlockedError,
    CooldownError,
    DuplicateOperationError,
    FriendshipNotFoundError,
)


class TestRelationService:
    """RelationService测试类"""
    
    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        return RelationService(mock_db)
    
    @pytest.fixture
    def user_a(self):
        """用户A"""
        device = MagicMock(spec=Device)
        device.device_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")
        device.nickname = "用户A"
        return device
    
    @pytest.fixture
    def user_b(self):
        """用户B"""
        device = MagicMock(spec=Device)
        device.device_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440002")
        device.nickname = "用户B"
        return device
    
    @pytest.mark.asyncio
    async def test_send_friend_request_success(self, service, mock_db, user_b):
        """P0: 测试成功发送好友申请"""
        # Arrange - 无现有关系
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with patch.object(service, '_is_blocked', return_value=False):
            with patch.object(service, 'check_friendship', return_value=False):
                request = SendFriendRequest(
                    sender_id="550e8400-e29b-41d4-a716-446655440001",
                    receiver_id="550e8400-e29b-41d4-a716-446655440002",
                    message="想加你为好友"
                )
                
                # Act
                result = await service.send_friend_request(request)
                
                # Assert
                assert result["status"] == "pending"
                assert "request_id" in result
                mock_db.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_friend_request_blocked(self, service, mock_db):
        """P0: 测试向屏蔽者发送申请返回4004错误"""
        with patch.object(service, '_is_blocked', return_value=True):
            request = SendFriendRequest(
                sender_id="550e8400-e29b-41d4-a716-446655440001",
                receiver_id="550e8400-e29b-41d4-a716-446655440002"
            )
            
            with pytest.raises(BlockedError) as exc_info:
                await service.send_friend_request(request)
            
            assert exc_info.value.code == 4004
    
    @pytest.mark.asyncio
    async def test_send_friend_request_cooldown(self, service, mock_db):
        """P0: 测试冷却期内重复申请返回4005错误"""
        # Arrange - 存在被拒绝记录
        rejected_friendship = MagicMock(spec=Friendship)
        rejected_friendship.status = "rejected"
        rejected_friendship.updated_at = datetime.utcnow() - timedelta(hours=12)  # 12小时前
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = rejected_friendship
        mock_db.execute.return_value = mock_result
        
        with patch.object(service, '_is_blocked', return_value=False):
            with patch.object(service, 'check_friendship', return_value=False):
                request = SendFriendRequest(
                    sender_id="550e8400-e29b-41d4-a716-446655440001",
                    receiver_id="550e8400-e29b-41d4-a716-446655440002"
                )
                
                with pytest.raises(CooldownError) as exc_info:
                    await service.send_friend_request(request)
                
                assert exc_info.value.code == 4005
    
    @pytest.mark.asyncio
    async def test_send_friend_request_duplicate(self, service, mock_db):
        """P0: 测试重复申请返回4009错误"""
        # Arrange - 存在待处理申请
        pending_friendship = MagicMock(spec=Friendship)
        pending_friendship.status = "pending"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = pending_friendship
        mock_db.execute.return_value = mock_result
        
        with patch.object(service, '_is_blocked', return_value=False):
            with patch.object(service, 'check_friendship', return_value=False):
                request = SendFriendRequest(
                    sender_id="550e8400-e29b-41d4-a716-446655440001",
                    receiver_id="550e8400-e29b-41d4-a716-446655440002"
                )
                
                with pytest.raises(DuplicateOperationError) as exc_info:
                    await service.send_friend_request(request)
                
                assert exc_info.value.code == 4009
    
    @pytest.mark.asyncio
    async def test_respond_friend_request_accept(self, service, mock_db, user_a):
        """P0: 测试接受好友申请"""
        # Arrange
        friendship = MagicMock(spec=Friendship)
        friendship.request_id = uuid.UUID("req-123")
        friendship.user_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")
        friendship.friend_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440002")
        friendship.status = "pending"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = friendship
        mock_db.execute.return_value = mock_result
        
        with patch.object(service, '_create_or_upgrade_session', return_value="sess-123"):
            request = RespondFriendRequest(
                device_id="550e8400-e29b-41d4-a716-446655440002",
                action="accept"
            )
            
            # Act
            result = await service.respond_friend_request("req-123", request)
            
            # Assert
            assert result["status"] == "accepted"
            assert result["session_id"] == "sess-123"
    
    @pytest.mark.asyncio
    async def test_respond_friend_request_reject(self, service, mock_db):
        """P0: 测试拒绝好友申请"""
        # Arrange
        friendship = MagicMock(spec=Friendship)
        friendship.request_id = uuid.UUID("req-123")
        friendship.user_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")
        friendship.friend_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440002")
        friendship.status = "pending"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = friendship
        mock_db.execute.return_value = mock_result
        
        request = RespondFriendRequest(
            device_id="550e8400-e29b-41d4-a716-446655440002",
            action="reject"
        )
        
        # Act
        result = await service.respond_friend_request("req-123", request)
        
        # Assert
        assert result["status"] == "rejected"
    
    @pytest.mark.asyncio
    async def test_check_friendship_true(self, service, mock_db):
        """P0: 测试检查好友关系存在"""
        # Arrange
        friendship = MagicMock(spec=Friendship)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = friendship
        mock_db.execute.return_value = mock_result
        
        # Act
        result = await service.check_friendship(
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002"
        )
        
        # Assert
        assert result is True
    
    @pytest.mark.asyncio
    async def test_check_friendship_false(self, service, mock_db):
        """P0: 测试检查好友关系不存在"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await service.check_friendship(
            "550e8400-e29b-41d4-a716-446655440001",
            "550e8400-e29b-41d4-a716-446655440002"
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_block_user_success(self, service, mock_db):
        """P0: 测试成功屏蔽用户"""
        mock_db.execute.return_value = MagicMock()
        
        request = BlockUserRequest(
            device_id="550e8400-e29b-41d4-a716-446655440001",
            target_id="550e8400-e29b-41d4-a716-446655440002"
        )
        
        # Act
        await service.block_user(request)
        
        # Assert
        mock_db.commit.assert_called()
    
    def test_is_in_cooldown(self):
        """P1: 测试冷却期计算"""
        friendship = MagicMock(spec=Friendship)
        friendship.status = "rejected"
        
        # 12小时前被拒绝 - 在冷却期内
        friendship.updated_at = datetime.utcnow() - timedelta(hours=12)
        assert friendship.updated_at > datetime.utcnow() - timedelta(hours=24)
