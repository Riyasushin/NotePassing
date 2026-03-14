"""
设备服务单元测试 - 测试DeviceService的实际实现
"""

import uuid
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.device_service import DeviceService
from app.schemas.device import DeviceInitRequest, DeviceUpdateRequest
from app.models import Device
from app.exceptions import ValidationError, DeviceNotInitializedError


class TestDeviceService:
    """DeviceService测试类"""
    
    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        return DeviceService(mock_db)
    
    @pytest.fixture
    def sample_device(self):
        """示例设备模型"""
        device = MagicMock(spec=Device)
        device.device_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")
        device.nickname = "测试用户"
        device.avatar = "https://example.com/avatar.jpg"
        device.tags = ["摄影", "旅行"]
        device.profile = "喜欢拍照"
        device.is_anonymous = False
        device.role_name = None
        device.created_at = datetime.utcnow()
        device.updated_at = None
        return device
    
    @pytest.mark.asyncio
    async def test_init_device_success_new_device(self, service, mock_db, sample_device):
        """P0: 测试新设备初始化成功"""
        # Arrange - 设备不存在
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        request = DeviceInitRequest(
            device_id="550e8400-e29b-41d4-a716-446655440001",
            nickname="测试用户",
            tags=["摄影"],
            profile="简介"
        )
        
        # Act
        result = await service.init_device(request)
        
        # Assert
        assert result["is_new"] is True
        assert result["nickname"] == "测试用户"
        assert result["device_id"] == request.device_id
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_init_device_success_existing_device(self, service, mock_db, sample_device):
        """P0: 测试已有设备恢复"""
        # Arrange - 设备已存在
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_device
        mock_db.execute.return_value = mock_result
        
        request = DeviceInitRequest(
            device_id="550e8400-e29b-41d4-a716-446655440001",
            nickname="新昵称",  # 尝试修改昵称
            tags=[],
            profile=""
        )
        
        # Act
        result = await service.init_device(request)
        
        # Assert - 应返回原有数据，不修改
        assert result["is_new"] is False
        assert result["nickname"] == "测试用户"  # 保持原昵称
        mock_db.add.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_init_device_invalid_uuid(self, service):
        """P0: 测试无效UUID返回5001错误"""
        request = DeviceInitRequest(
            device_id="invalid-uuid",
            nickname="测试用户"
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await service.init_device(request)
        
        assert exc_info.value.code == 5001
    
    @pytest.mark.asyncio
    async def test_init_device_nickname_too_long(self, service):
        """P1: 测试超长昵称返回5001错误"""
        request = DeviceInitRequest(
            device_id="550e8400-e29b-41d4-a716-446655440001",
            nickname="a" * 51  # 51字符，超过限制
        )
        
        with pytest.raises(ValidationError) as exc_info:
            await service.init_device(request)
        
        assert exc_info.value.code == 5001
    
    @pytest.mark.asyncio
    async def test_get_device_profile_friend(self, service, mock_db, sample_device):
        """P0: 测试获取好友资料返回完整信息"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_device
        mock_db.execute.return_value = mock_result
        
        # Mock好友关系检查
        with patch("app.services.relation_service.RelationService.check_friendship") as mock_check:
            mock_check.return_value = True
            
            # Act
            result = await service.get_device_profile(
                target_id="550e8400-e29b-41d4-a716-446655440001",
                requester_id="550e8400-e29b-41d4-a716-446655440002"
            )
        
        # Assert
        assert result["is_friend"] is True
        assert result["avatar"] == "https://example.com/avatar.jpg"
        assert result["nickname"] == "测试用户"
    
    @pytest.mark.asyncio
    async def test_get_device_profile_stranger_anonymous(self, service, mock_db, sample_device):
        """P0: 测试获取陌生人匿名资料隐藏头像"""
        # Arrange
        sample_device.is_anonymous = True
        sample_device.role_name = "神秘人"
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_device
        mock_db.execute.return_value = mock_result
        
        with patch("app.services.relation_service.RelationService.check_friendship") as mock_check:
            mock_check.return_value = False
            
            # Act
            result = await service.get_device_profile(
                target_id="550e8400-e29b-41d4-a716-446655440001",
                requester_id="550e8400-e29b-41d4-a716-446655440002"
            )
        
        # Assert
        assert result["is_friend"] is False
        assert result["avatar"] is None  # 头像被隐藏
        assert result["nickname"] == "神秘人"  # 显示角色名
    
    @pytest.mark.asyncio
    async def test_get_device_profile_not_found(self, service, mock_db):
        """P0: 测试获取不存在的设备返回4007错误"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with pytest.raises(DeviceNotInitializedError) as exc_info:
            await service.get_device_profile(
                target_id="550e8400-e29b-41d4-a716-446655440001",
                requester_id="550e8400-e29b-41d4-a716-446655440002"
            )
        
        assert exc_info.value.code == 4007
    
    @pytest.mark.asyncio
    async def test_update_device_partial(self, service, mock_db, sample_device):
        """P0: 测试部分更新只修改指定字段"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_device
        mock_db.execute.return_value = mock_result
        
        request = DeviceUpdateRequest(nickname="新昵称")  # 只更新昵称
        
        # Act
        result = await service.update_device(
            device_id="550e8400-e29b-41d4-a716-446655440001",
            request=request
        )
        
        # Assert
        assert result["nickname"] == "新昵称"
        # 其他字段应保持不变
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_update_device_not_found(self, service, mock_db):
        """P1: 测试更新不存在的设备返回4007错误"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        request = DeviceUpdateRequest(nickname="新昵称")
        
        with pytest.raises(DeviceNotInitializedError) as exc_info:
            await service.update_device(
                device_id="550e8400-e29b-41d4-a716-446655440001",
                request=request
            )
        
        assert exc_info.value.code == 4007


class TestDeviceValidators:
    """设备验证工具测试"""
    
    def test_is_valid_uuid_valid(self):
        """测试有效UUID验证"""
        from app.utils.validators import is_valid_uuid
        
        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440001",
            "12345678-1234-1234-1234-123456789abc",
        ]
        
        for uuid_str in valid_uuids:
            assert is_valid_uuid(uuid_str) is True
    
    def test_is_valid_uuid_invalid(self):
        """测试无效UUID验证"""
        from app.utils.validators import is_valid_uuid
        
        invalid_uuids = [
            "invalid-uuid",
            "550e8400",
            "",
            "550e8400-e29b-41d4-a716",  # 不完整
        ]
        
        for uuid_str in invalid_uuids:
            assert is_valid_uuid(uuid_str) is False
    
    def test_validate_nickname(self):
        """测试昵称验证"""
        from app.utils.validators import validate_nickname
        
        # 有效昵称
        assert validate_nickname("正常昵称") == (True, "")
        assert validate_nickname("a" * 50) == (True, "")
        
        # 无效昵称
        assert validate_nickname("") == (False, "昵称不能为空")
        assert validate_nickname("a" * 51) == (False, "昵称长度不能超过50字符")
