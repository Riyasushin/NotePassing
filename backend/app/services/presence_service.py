"""
附近关系服务 - 处理附近设备发现和Boost
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from sqlalchemy import select, update, insert, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Presence, Device, Session, Block
from app.schemas import (
    PresenceResolveRequest,
    PresenceDisconnectRequest,
    NearbyDevice,
    BoostAlert,
)
from app.utils import is_valid_uuid, rssi_to_distance_simple
from app.exceptions import ValidationError


class PresenceService:
    """附近关系服务类"""
    
    # Boost冷却时间（分钟）
    BOOST_COOLDOWN_MINUTES = 5
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def resolve_nearby_devices(
        self,
        request: PresenceResolveRequest
    ) -> dict:
        """
        解析附近设备
        
        将临时ID解析为设备信息，应用隐私过滤
        
        Args:
            request: 解析请求
            
        Returns:
            附近设备列表和Boost提醒
        """
        if not is_valid_uuid(request.device_id):
            raise ValidationError("device_id格式错误")
        
        device_uuid = uuid.UUID(request.device_id)
        
        # 验证请求者设备存在
        result = await self.db.execute(
            select(Device).where(Device.device_id == device_uuid)
        )
        if not result.scalar_one_or_none():
            raise ValidationError("设备未初始化")
        
        # 获取被屏蔽的用户列表
        blocked_by_me = await self._get_blocked_users(device_uuid)
        blocking_me = await self._get_blocking_users(device_uuid)
        blocked_set = set(blocked_by_me + blocking_me)
        
        # 临时ID解析为设备ID
        from app.services.temp_id_service import TempIdService
        temp_service = TempIdService(self.db)
        
        temp_ids = [d.temp_id for d in request.scanned_devices]
        temp_to_device = await temp_service.batch_resolve_temp_ids(temp_ids)
        
        # 构建RSSI映射
        rssi_map = {d.temp_id: d.rssi for d in request.scanned_devices}
        
        # 准备结果
        nearby_devices = []
        boost_alerts = []
        
        # 查询所有设备的资料
        device_ids = list(temp_to_device.values())
        if device_ids:
            result = await self.db.execute(
                select(Device).where(Device.device_id.in_(
                    [uuid.UUID(did) for did in device_ids]
                ))
            )
            devices = {str(d.device_id): d for d in result.scalars().all()}
            
            # 查询好友关系
            from app.services.relation_service import RelationService
            relation_service = RelationService(self.db)
            
            for temp_id, target_id in temp_to_device.items():
                # 跳过被屏蔽的用户
                if target_id in blocked_set:
                    continue
                
                device = devices.get(target_id)
                if not device:
                    continue
                
                # 检查是否为好友
                is_friend = await relation_service.check_friendship(
                    request.device_id,
                    target_id
                )
                
                # 计算距离
                rssi = rssi_map.get(temp_id, -70)
                distance = rssi_to_distance_simple(rssi)
                
                # 构建设备信息
                device_info = self._build_device_info(
                    temp_id=temp_id,
                    device=device,
                    is_friend=is_friend,
                    distance=distance
                )
                nearby_devices.append(device_info)
                
                # 更新附近关系
                await self._update_presence(device_uuid, device.device_id)
                
                # 检查是否需要触发Boost
                if is_friend:
                    should_boost = await self._check_and_trigger_boost(
                        device_uuid,
                        device.device_id,
                        device.nickname,
                        distance
                    )
                    if should_boost:
                        boost_alerts.append({
                            "device_id": target_id,
                            "nickname": device.nickname,
                            "distance_estimate": distance,
                        })
        
        return {
            "nearby_devices": nearby_devices,
            "boost_alerts": boost_alerts,
        }
    
    async def report_disconnect(
        self,
        request: PresenceDisconnectRequest
    ) -> dict:
        """
        上报离开范围
        
        标记附近关系断开，过期临时会话
        
        Args:
            request: 断开请求
            
        Returns:
            会话过期信息
        """
        if not is_valid_uuid(request.device_id):
            raise ValidationError("device_id格式错误")
        if not is_valid_uuid(request.left_device_id):
            raise ValidationError("left_device_id格式错误")
        
        device_uuid = uuid.UUID(request.device_id)
        left_uuid = uuid.UUID(request.left_device_id)
        
        # 更新附近关系
        await self.db.execute(
            update(Presence)
            .where(
                and_(
                    Presence.user_id == device_uuid,
                    Presence.nearby_user_id == left_uuid
                )
            )
            .values(last_disconnect_at=datetime.utcnow())
        )
        
        # 查找并过期临时会话
        result = await self.db.execute(
            select(Session)
            .where(
                and_(
                    or_(
                        and_(
                            Session.user1_id == device_uuid,
                            Session.user2_id == left_uuid
                        ),
                        and_(
                            Session.user1_id == left_uuid,
                            Session.user2_id == device_uuid
                        )
                    ),
                    Session.is_temp == True,
                    Session.expired_at == None
                )
            )
        )
        session = result.scalar_one_or_none()
        
        session_expired = False
        session_id = None
        
        if session:
            session.expired_at = datetime.utcnow()
            session_expired = True
            session_id = str(session.session_id)
            await self.db.commit()
        
        return {
            "session_expired": session_expired,
            "session_id": session_id,
        }
    
    def _build_device_info(
        self,
        temp_id: str,
        device: Device,
        is_friend: bool,
        distance: float
    ) -> dict:
        """
        构建设备信息，应用隐私过滤
        """
        info = {
            "temp_id": temp_id,
            "device_id": str(device.device_id),
            "nickname": device.nickname,
            "tags": device.tags or [],
            "profile": device.profile or "",
            "is_anonymous": device.is_anonymous,
            "role_name": device.role_name,
            "distance_estimate": distance,
            "is_friend": is_friend,
        }
        
        # 陌生人且匿名模式：隐藏头像，使用role_name作为昵称
        if not is_friend and device.is_anonymous:
            info["avatar"] = None
            if device.role_name:
                info["nickname"] = device.role_name
        else:
            info["avatar"] = device.avatar
        
        return info
    
    async def _update_presence(
        self,
        user_id: uuid.UUID,
        nearby_user_id: uuid.UUID
    ) -> None:
        """
        更新附近关系
        """
        # 使用INSERT ... ON CONFLICT DO UPDATE
        stmt = insert(Presence).values(
            user_id=user_id,
            nearby_user_id=nearby_user_id,
            last_seen_at=datetime.utcnow()
        ).on_conflict_do_update(
            index_elements=["user_id", "nearby_user_id"],
            set_={"last_seen_at": datetime.utcnow()}
        )
        
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def _check_and_trigger_boost(
        self,
        user_id: uuid.UUID,
        friend_id: uuid.UUID,
        friend_nickname: str,
        distance: float
    ) -> bool:
        """
        检查并触发Boost
        
        条件：
        1. 对方是好友
        2. 距离上次Boost超过5分钟
        
        Returns:
            是否触发了Boost
        """
        # 查询或创建presence记录
        result = await self.db.execute(
            select(Presence)
            .where(
                and_(
                    Presence.user_id == user_id,
                    Presence.nearby_user_id == friend_id
                )
            )
        )
        presence = result.scalar_one_or_none()
        
        if not presence:
            # 首次发现，创建记录并触发Boost
            presence = Presence(
                user_id=user_id,
                nearby_user_id=friend_id,
                last_seen_at=datetime.utcnow(),
                last_boost_at=datetime.utcnow()
            )
            self.db.add(presence)
            await self.db.commit()
            return True
        
        # 检查冷却期
        if presence.can_trigger_boost(self.BOOST_COOLDOWN_MINUTES):
            presence.last_boost_at = datetime.utcnow()
            await self.db.commit()
            return True
        
        return False
    
    async def _get_blocked_users(self, device_id: uuid.UUID) -> List[str]:
        """获取被屏蔽的用户列表"""
        result = await self.db.execute(
            select(Block.target_id)
            .where(Block.blocker_id == device_id)
        )
        return [str(tid) for tid in result.scalars().all()]
    
    async def _get_blocking_users(self, device_id: uuid.UUID) -> List[str]:
        """获取屏蔽该用户的用户列表"""
        result = await self.db.execute(
            select(Block.blocker_id)
            .where(Block.target_id == device_id)
        )
        return [str(bid) for bid in result.scalars().all()]
