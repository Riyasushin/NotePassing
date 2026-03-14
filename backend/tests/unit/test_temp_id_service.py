"""
临时ID服务单元测试 - 测试TempIdService的实际实现
"""

import uuid
import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from app.services.temp_id_service import TempIdService
from app.schemas.temp_id import TempIdRefreshRequest
from app.models import TempId, Device
from app.exceptions import ValidationError, DeviceNotInitializedError


class TestTempIdService:
    """TempIdService测试类"""
    
    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        return TempIdService(mock_db)
    
    @pytest.fixture
    def sample_device(self):
        """示例设备"""
        device = MagicMock(spec=Device)
        device.device_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")
        return device
    
    @pytest.mark.asyncio
    async def test_refresh_temp_id_success(self, service, mock_db, sample_device):
        """P0: 测试成功生成临时ID"""
        # Arrange
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = sample_device
        mock_db.execute.return_value = mock_result
        
        request = TempIdRefreshRequest(
            device_id="550e8400-e29b-41d4-a716-446655440001"
        )
        
        # Act
        result = await service.refresh_temp_id(request)
        
        # Assert
        assert len(result["temp_id"]) == 32
        assert all(c in '0123456789abcdef' for c in result["temp_id"])
        assert "expires_at" in result
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called()
    
    @pytest.mark.asyncio
    async def test_refresh_temp_id_device_not_found(self, service, mock_db):
        """P1: 测试设备不存在返回4007错误"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        request = TempIdRefreshRequest(
            device_id="550e8400-e29b-41d4-a716-446655440001"
        )
        
        with pytest.raises(DeviceNotInitializedError) as exc_info:
            await service.refresh_temp_id(request)
        
        assert exc_info.value.code == 4007
    
    @pytest.mark.asyncio
    async def test_resolve_temp_id_success(self, service, mock_db):
        """P0: 测试成功解析临时ID"""
        # Arrange
        temp_id = MagicMock(spec=TempId)
        temp_id.device_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")
        temp_id.expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = temp_id
        mock_db.execute.return_value = mock_result
        
        # Act
        result = await service.resolve_temp_id("a1b2c3d4e5f6789012345678abcdef01")
        
        # Assert
        assert result == "550e8400-e29b-41d4-a716-446655440001"
    
    @pytest.mark.asyncio
    async def test_resolve_temp_id_expired(self, service, mock_db):
        """P0: 测试解析过期临时ID返回None"""
        # Arrange - 已过期（超过缓冲期）
        temp_id = MagicMock(spec=TempId)
        temp_id.device_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")
        temp_id.expires_at = datetime.utcnow() - timedelta(minutes=10)  # 已过期超过缓冲期
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = temp_id
        mock_db.execute.return_value = mock_result
        
        # Act
        result = await service.resolve_temp_id("a1b2c3d4e5f6789012345678abcdef01")
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_resolve_temp_id_not_found(self, service, mock_db):
        """P1: 测试解析不存在的临时ID返回None"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        result = await service.resolve_temp_id("nonexistent")
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_batch_resolve_temp_ids(self, service, mock_db):
        """P0: 测试批量解析临时ID"""
        # Arrange
        temp_id1 = MagicMock(spec=TempId)
        temp_id1.temp_id = "tempid1tempid1tempid1tempid12"
        temp_id1.device_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440001")
        temp_id1.expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        temp_id2 = MagicMock(spec=TempId)
        temp_id2.temp_id = "tempid2tempid2tempid2tempid22"
        temp_id2.device_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440002")
        temp_id2.expires_at = datetime.utcnow() - timedelta(minutes=10)  # 已过期
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [temp_id1, temp_id2]
        mock_db.execute.return_value = mock_result
        
        # Act
        result = await service.batch_resolve_temp_ids([
            "tempid1tempid1tempid1tempid12",
            "tempid2tempid2tempid2tempid22"
        ])
        
        # Assert - 只返回未过期的
        assert "tempid1tempid1tempid1tempid12" in result
        assert "tempid2tempid2tempid2tempid22" not in result


class TestTempIdGenerator:
    """临时ID生成器测试"""
    
    def test_generate_temp_id_format(self):
        """测试生成的临时ID格式"""
        from app.utils.temp_id_generator import generate_temp_id_simple
        
        temp_id, expires_at = generate_temp_id_simple("device123")
        
        # 应为32字符十六进制
        assert len(temp_id) == 32
        assert all(c in '0123456789abcdef' for c in temp_id)
        
        # 过期时间应在5分钟后
        from datetime import datetime
        expected_expires = datetime.utcnow() + timedelta(minutes=5)
        assert abs((expires_at - expected_expires).total_seconds()) < 1
