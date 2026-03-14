"""
设备服务 - 处理设备相关的业务逻辑
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Device
from app.schemas import DeviceInitRequest, DeviceUpdateRequest
from app.utils import is_valid_uuid, validate_nickname, validate_profile
from app.exceptions import (
    ValidationError,
    DeviceNotInitializedError,
)


class DeviceService:
    """设备服务类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def init_device(self, request: DeviceInitRequest) -> dict:
        """
        初始化设备
        
        如果设备已存在则返回现有信息，否则创建新设备
        
        Args:
            request: 初始化请求
            
        Returns:
            设备信息，包含is_new标志
        """
        # 验证UUID格式
        if not is_valid_uuid(request.device_id):
            raise ValidationError("device_id格式错误，应为UUID v4")
        
        # 验证昵称
        valid, error = validate_nickname(request.nickname)
        if not valid:
            raise ValidationError(error)
        
        # 检查设备是否已存在
        device_id = uuid.UUID(request.device_id)
        result = await self.db.execute(
            select(Device).where(Device.device_id == device_id)
        )
        existing_device = result.scalar_one_or_none()
        
        if existing_device:
            # 返回现有设备
            return {
                "device_id": str(existing_device.device_id),
                "nickname": existing_device.nickname,
                "is_new": False,
                "created_at": existing_device.created_at.isoformat(),
            }
        
        # 创建新设备
        new_device = Device(
            device_id=device_id,
            nickname=request.nickname,
            tags=request.tags or [],
            profile=request.profile or "",
            is_anonymous=False,
        )
        
        self.db.add(new_device)
        await self.db.commit()
        
        return {
            "device_id": str(new_device.device_id),
            "nickname": new_device.nickname,
            "is_new": True,
            "created_at": new_device.created_at.isoformat(),
        }
    
    async def get_device_profile(
        self,
        target_id: str,
        requester_id: str
    ) -> dict:
        """
        获取设备资料
        
        根据请求者与目标的关系，应用隐私过滤规则
        
        Args:
            target_id: 目标设备ID
            requester_id: 请求者设备ID
            
        Returns:
            过滤后的设备资料
        """
        from app.services.relation_service import RelationService
        
        # 验证UUID
        if not is_valid_uuid(target_id):
            raise ValidationError("device_id格式错误")
        
        target_uuid = uuid.UUID(target_id)
        
        # 查询目标设备
        result = await self.db.execute(
            select(Device).where(Device.device_id == target_uuid)
        )
        target = result.scalar_one_or_none()
        
        if not target:
            raise DeviceNotInitializedError()
        
        # 检查是否为好友
        relation_service = RelationService(self.db)
        is_friend = await relation_service.check_friendship(
            requester_id, target_id
        )
        
        # 应用隐私过滤
        profile = {
            "device_id": str(target.device_id),
            "nickname": target.nickname,
            "tags": target.tags or [],
            "profile": target.profile or "",
            "is_anonymous": target.is_anonymous,
            "role_name": target.role_name,
            "is_friend": is_friend,
        }
        
        # 陌生人且匿名模式：隐藏头像，显示role_name
        if not is_friend and target.is_anonymous:
            profile["avatar"] = None
            if target.role_name:
                profile["nickname"] = target.role_name
        else:
            profile["avatar"] = target.avatar
        
        return profile
    
    async def update_device(
        self,
        device_id: str,
        request: DeviceUpdateRequest
    ) -> dict:
        """
        更新设备资料
        
        支持部分更新，只更新提供的字段
        
        Args:
            device_id: 设备ID
            request: 更新请求
            
        Returns:
            更新后的设备资料
        """
        # 验证UUID
        if not is_valid_uuid(device_id):
            raise ValidationError("device_id格式错误")
        
        device_uuid = uuid.UUID(device_id)
        
        # 检查设备是否存在
        result = await self.db.execute(
            select(Device).where(Device.device_id == device_uuid)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            raise DeviceNotInitializedError()
        
        # 验证并更新字段
        update_data = {}
        
        if request.nickname is not None:
            valid, error = validate_nickname(request.nickname)
            if not valid:
                raise ValidationError(error)
            update_data["nickname"] = request.nickname
        
        if request.profile is not None:
            valid, error = validate_profile(request.profile)
            if not valid:
                raise ValidationError(error)
            update_data["profile"] = request.profile
        
        if request.avatar is not None:
            update_data["avatar"] = request.avatar
        
        if request.tags is not None:
            update_data["tags"] = request.tags
        
        if request.is_anonymous is not None:
            update_data["is_anonymous"] = request.is_anonymous
        
        if request.role_name is not None:
            if len(request.role_name) > 50:
                raise ValidationError("角色名长度不能超过50字符")
            update_data["role_name"] = request.role_name
        
        # 添加更新时间
        update_data["updated_at"] = datetime.utcnow()
        
        # 执行更新
        await self.db.execute(
            update(Device)
            .where(Device.device_id == device_uuid)
            .values(**update_data)
        )
        await self.db.commit()
        
        # 刷新设备信息
        result = await self.db.execute(
            select(Device).where(Device.device_id == device_uuid)
        )
        updated_device = result.scalar_one()
        
        return {
            "device_id": str(updated_device.device_id),
            "nickname": updated_device.nickname,
            "avatar": updated_device.avatar,
            "tags": updated_device.tags or [],
            "profile": updated_device.profile or "",
            "is_anonymous": updated_device.is_anonymous,
            "role_name": updated_device.role_name,
            "updated_at": updated_device.updated_at.isoformat(),
        }
    
    async def get_device_by_id(self, device_id: str) -> Optional[Device]:
        """
        根据ID获取设备
        
        Args:
            device_id: 设备ID字符串
            
        Returns:
            设备对象，不存在则返回None
        """
        if not is_valid_uuid(device_id):
            return None
        
        device_uuid = uuid.UUID(device_id)
        result = await self.db.execute(
            select(Device).where(Device.device_id == device_uuid)
        )
        return result.scalar_one_or_none()
    
    async def check_device_exists(self, device_id: str) -> bool:
        """
        检查设备是否存在
        
        Args:
            device_id: 设备ID字符串
            
        Returns:
            是否存在
        """
        device = await self.get_device_by_id(device_id)
        return device is not None
