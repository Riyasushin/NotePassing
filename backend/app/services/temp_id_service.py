"""
临时ID服务 - 处理临时ID的生成和解析
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TempId, Device
from app.schemas import TempIdRefreshRequest
from app.utils import generate_temp_id_simple, is_valid_uuid
from app.exceptions import DeviceNotInitializedError, ValidationError
from app.config import settings


class TempIdService:
    """临时ID服务类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def refresh_temp_id(
        self,
        request: TempIdRefreshRequest
    ) -> dict:
        """
        刷新临时ID
        
        生成新的临时ID，可选延长旧ID的缓冲期
        
        Args:
            request: 刷新请求
            
        Returns:
            新的临时ID和过期时间
        """
        # 验证设备ID
        if not is_valid_uuid(request.device_id):
            raise ValidationError("device_id格式错误")
        
        device_uuid = uuid.UUID(request.device_id)
        
        # 检查设备是否存在
        result = await self.db.execute(
            select(Device).where(Device.device_id == device_uuid)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            raise DeviceNotInitializedError()
        
        # 如果提供了当前临时ID，延长其缓冲期
        if request.current_temp_id:
            await self._extend_buffer_period(request.current_temp_id)
        
        # 生成新的临时ID
        new_temp_id, expires_at = generate_temp_id_simple(request.device_id)
        
        # 保存到数据库
        temp_id_record = TempId(
            temp_id=new_temp_id,
            device_id=device_uuid,
            expires_at=expires_at,
        )
        self.db.add(temp_id_record)
        await self.db.commit()
        
        # 清理过期的临时ID（异步，不阻塞）
        await self._cleanup_expired_temp_ids()
        
        return {
            "temp_id": new_temp_id,
            "expires_at": expires_at.isoformat(),
        }
    
    async def resolve_temp_id(self, temp_id: str) -> Optional[str]:
        """
        解析临时ID为设备ID
        
        Args:
            temp_id: 临时ID字符串
            
        Returns:
            设备ID字符串，不存在或已过期则返回None
        """
        if not temp_id or len(temp_id) != 32:
            return None
        
        # 查询数据库
        result = await self.db.execute(
            select(TempId)
            .where(TempId.temp_id == temp_id)
        )
        temp_record = result.scalar_one_or_none()
        
        if not temp_record:
            return None
        
        # 检查是否已过期（包括5分钟缓冲期）
        buffer_expires = temp_record.expires_at + timedelta(minutes=5)
        if datetime.utcnow() > buffer_expires:
            return None
        
        return str(temp_record.device_id)
    
    async def batch_resolve_temp_ids(
        self,
        temp_ids: list[str]
    ) -> dict[str, str]:
        """
        批量解析临时ID
        
        Args:
            temp_ids: 临时ID列表
            
        Returns:
            {temp_id: device_id} 映射字典
        """
        if not temp_ids:
            return {}
        
        # 查询所有有效的临时ID
        result = await self.db.execute(
            select(TempId)
            .where(TempId.temp_id.in_(temp_ids))
        )
        records = result.scalars().all()
        
        # 过滤掉已过期的
        valid_mapping = {}
        now = datetime.utcnow()
        
        for record in records:
            buffer_expires = record.expires_at + timedelta(minutes=5)
            if now <= buffer_expires:
                valid_mapping[record.temp_id] = str(record.device_id)
        
        return valid_mapping
    
    async def _extend_buffer_period(self, temp_id: str) -> None:
        """
        延长临时ID的缓冲期
        
        将过期时间更新为当前时间+5分钟
        """
        new_expires = datetime.utcnow() + timedelta(minutes=5)
        
        await self.db.execute(
            update(TempId)
            .where(TempId.temp_id == temp_id)
            .values(expires_at=new_expires)
        )
        await self.db.commit()
    
    async def _cleanup_expired_temp_ids(self) -> None:
        """
        清理已过期的临时ID
        
        删除超过缓冲期的记录
        """
        cutoff = datetime.utcnow() - timedelta(minutes=5)
        
        await self.db.execute(
            delete(TempId)
            .where(TempId.expires_at < cutoff)
        )
        await self.db.commit()
