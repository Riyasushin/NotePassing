"""
消息服务单元测试 - 测试MessagingService的实际实现
"""

import uuid
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.services.messaging_service import MessagingService
from app.schemas.message import SendMessageRequest, MarkReadRequest
from app.models import Message, Session, Device
from app.exceptions import (
    ValidationError,
    DeviceNotInitializedError,
    BlockedError,
    TempMessageLimitError,
)


class TestMessagingService:
    """MessagingService测试类"""
    
    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        return MessagingService(mock_db)
    
    @pytest.fixture
    def sender(self):
        """发送者"""
        device = MagicMock(spec=Device)
        device.device_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")
        return device
    
    @pytest.fixture
    def receiver(self):
        """接收者"""
        device = MagicMock(spec=Device)
        device.device_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440002")
        return device
    
    @pytest.mark.asyncio
    async def test_send_message_friend_success(self, service, mock_db, sender, receiver):
        """P0: 测试好友间发送消息成功"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [sender, receiver, None]  # sender, receiver, session
        mock_db.execute.return_value = mock_result
        
        with patch("app.services.relation_service.RelationService._is_blocked", return_value=False):
            with patch("app.services.relation_service.RelationService.check_friendship", return_value=True):
                request = SendMessageRequest(
                    sender_id="550e8400-e29b-41d4-a716-446655440001",
                    receiver_id="550e8400-e29b-41d4-a716-446655440002",
                    content="你好，朋友！",
                    type="common"
                )
                
                # Act
                result = await service.send_message(request)
                
                # Assert
                assert result["status"] == "sent"
                assert "message_id" in result
                assert "session_id" in result
                mock_db.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_message_blocked(self, service, mock_db, sender, receiver):
        """P0: 测试向屏蔽者发送消息返回4004错误"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [sender, receiver]
        mock_db.execute.return_value = mock_result
        
        with patch("app.services.relation_service.RelationService._is_blocked", return_value=True):
            request = SendMessageRequest(
                sender_id="550e8400-e29b-41d4-a716-446655440001",
                receiver_id="550e8400-e29b-41d4-a716-446655440002",
                content="你好"
            )
            
            with pytest.raises(BlockedError) as exc_info:
                await service.send_message(request)
            
            assert exc_info.value.code == 4004
    
    @pytest.mark.asyncio
    async def test_send_message_stranger_first_two(self, service, mock_db, sender, receiver):
        """P0: 测试陌生人前两条消息成功"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [sender, receiver, None]
        mock_result.scalar.return_value = 0  # 消息计数为0
        mock_db.execute.return_value = mock_result
        
        with patch("app.services.relation_service.RelationService._is_blocked", return_value=False):
            with patch("app.services.relation_service.RelationService.check_friendship", return_value=False):
                request = SendMessageRequest(
                    sender_id="550e8400-e29b-41d4-a716-446655440001",
                    receiver_id="550e8400-e29b-41d4-a716-446655440002",
                    content="你好"
                )
                
                result = await service.send_message(request)
                
                assert result["status"] == "sent"
    
    @pytest.mark.asyncio
    async def test_send_message_invalid_type(self, service):
        """P1: 测试无效消息类型返回5001错误"""
        request = SendMessageRequest(
            sender_id="550e8400-e29b-41d4-a716-446655440001",
            receiver_id="550e8400-e29b-41d4-a716-446655440002",
            content="你好",
            type="invalid_type"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await service.send_message(request)
        
        assert exc_info.value.code == 5001
    
    @pytest.mark.asyncio
    async def test_send_message_content_too_long(self, service):
        """P1: 测试超长消息内容返回5001错误"""
        request = SendMessageRequest(
            sender_id="550e8400-e29b-41d4-a716-446655440001",
            receiver_id="550e8400-e29b-41d4-a716-446655440002",
            content="a" * 1001  # 超过1000字符限制
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await service.send_message(request)
        
        assert exc_info.value.code == 5001
    
    @pytest.mark.asyncio
    async def test_mark_messages_read_success(self, service, mock_db):
        """P0: 测试标记消息已读成功"""
        mock_db.execute.return_value = MagicMock(rowcount=2)
        
        request = MarkReadRequest(
            device_id="550e8400-e29b-41d4-a716-446655440002",
            message_ids=["msg-1", "msg-2"]
        )
        
        result = await service.mark_messages_read(request)
        
        assert result["updated_count"] == 2


class TestMessageValidation:
    """消息验证测试"""
    
    def test_validate_message_content_valid(self):
        """测试有效消息内容验证"""
        from app.utils.validators import validate_message_content
        
        assert validate_message_content("正常消息") == (True, "")
        assert validate_message_content("a" * 1000) == (True, "")
    
    def test_validate_message_content_invalid(self):
        """测试无效消息内容验证"""
        from app.utils.validators import validate_message_content
        
        assert validate_message_content("") == (False, "消息内容不能为空")
        assert validate_message_content("a" * 1001) == (False, "消息内容不能超过1000字符")
