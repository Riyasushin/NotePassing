"""
消息服务 - 处理消息发送、接收和历史记录
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Message, Session, Device
from app.schemas import SendMessageRequest, MarkReadRequest
from app.utils import is_valid_uuid, validate_message_content
from app.exceptions import (
    ValidationError,
    DeviceNotInitializedError,
    FriendshipNotFoundError,
    BlockedError,
    TempMessageLimitError,
)


class MessagingService:
    """消息服务类"""
    
    # 陌生人消息限制（未回复前最多2条）
    TEMP_MESSAGE_LIMIT = 2
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def send_message(
        self,
        request: SendMessageRequest
    ) -> dict:
        """
        发送消息
        
        Args:
            request: 发送消息请求
            
        Returns:
            消息信息
        """
        # 验证ID
        if not is_valid_uuid(request.sender_id):
            raise ValidationError("sender_id格式错误")
        if not is_valid_uuid(request.receiver_id):
            raise ValidationError("receiver_id格式错误")
        
        # 验证消息内容
        valid, error = validate_message_content(request.content)
        if not valid:
            raise ValidationError(error)
        
        # 验证消息类型
        if request.type not in ["common", "heartbeat"]:
            raise ValidationError("消息类型必须是common或heartbeat")
        
        sender_uuid = uuid.UUID(request.sender_id)
        receiver_uuid = uuid.UUID(request.receiver_id)
        
        # 检查设备是否存在
        sender = await self._get_device(sender_uuid)
        receiver = await self._get_device(receiver_uuid)
        
        if not sender:
            raise DeviceNotInitializedError()
        if not receiver:
            raise ValidationError("接收者不存在")
        
        # 检查是否被屏蔽
        from app.services.relation_service import RelationService
        relation_service = RelationService(self.db)
        
        is_blocked = await relation_service._is_blocked(
            request.receiver_id,
            request.sender_id
        )
        if is_blocked:
            raise BlockedError()
        
        # 检查是否为好友
        is_friend = await relation_service.check_friendship(
            request.sender_id,
            request.receiver_id
        )
        
        # 获取或创建会话
        session = await self._get_or_create_session(
            sender_uuid,
            receiver_uuid
        )
        
        # 检查临时会话的消息限制
        if not is_friend and session.is_temp:
            can_send = await self._check_temp_message_limit(
                session.session_id,
                sender_uuid,
                receiver_uuid
            )
            if not can_send:
                raise TempMessageLimitError()
        
        # 创建消息
        message = Message(
            session_id=session.session_id,
            sender_id=sender_uuid,
            receiver_id=receiver_uuid,
            content=request.content,
            type=request.type,
            status="sent",
        )
        
        self.db.add(message)
        await self.db.commit()
        
        return {
            "message_id": str(message.message_id),
            "session_id": str(session.session_id),
            "status": message.status,
            "created_at": message.created_at.isoformat(),
        }
    
    async def get_message_history(
        self,
        session_id: str,
        device_id: str,
        before: Optional[str] = None,
        limit: int = 20
    ) -> dict:
        """
        获取消息历史
        
        Args:
            session_id: 会话ID
            device_id: 请求者设备ID
            before: 分页游标（时间戳）
            limit: 每页条数
            
        Returns:
            消息列表
        """
        if not is_valid_uuid(session_id):
            raise ValidationError("session_id格式错误")
        if not is_valid_uuid(device_id):
            raise ValidationError("device_id格式错误")
        
        session_uuid = uuid.UUID(session_id)
        device_uuid = uuid.UUID(device_id)
        
        # 检查会话是否存在且用户是参与者
        result = await self.db.execute(
            select(Session)
            .where(
                and_(
                    Session.session_id == session_uuid,
                    or_(
                        Session.user1_id == device_uuid,
                        Session.user2_id == device_uuid
                    )
                )
            )
        )
        session = result.scalar_one_or_none()
        
        if not session:
            raise FriendshipNotFoundError()
        
        # 构建查询
        query = select(Message).where(
            Message.session_id == session_uuid
        )
        
        # 分页游标
        if before:
            try:
                before_time = datetime.fromisoformat(before)
                query = query.where(Message.created_at < before_time)
            except ValueError:
                pass
        
        # 排序和限制
        query = query.order_by(Message.created_at.desc()).limit(limit + 1)
        
        result = await self.db.execute(query)
        messages = result.scalars().all()
        
        # 检查是否有更多
        has_more = len(messages) > limit
        messages = messages[:limit]
        
        # 转换为响应格式
        message_items = [
            {
                "message_id": str(msg.message_id),
                "sender_id": str(msg.sender_id),
                "content": msg.content,
                "type": msg.type,
                "status": msg.status,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in messages
        ]
        
        return {
            "session_id": session_id,
            "messages": message_items,
            "has_more": has_more,
        }
    
    async def mark_messages_read(
        self,
        request: MarkReadRequest
    ) -> dict:
        """
        标记消息为已读
        
        Args:
            request: 标记已读请求
            
        Returns:
            更新数量
        """
        if not is_valid_uuid(request.device_id):
            raise ValidationError("device_id格式错误")
        
        device_uuid = uuid.UUID(request.device_id)
        
        # 转换消息ID列表
        message_ids = []
        for msg_id in request.message_ids:
            if is_valid_uuid(msg_id):
                message_ids.append(uuid.UUID(msg_id))
        
        if not message_ids:
            return {"updated_count": 0}
        
        # 只更新接收者是当前用户的消息
        result = await self.db.execute(
            update(Message)
            .where(
                and_(
                    Message.message_id.in_(message_ids),
                    Message.receiver_id == device_uuid,
                    Message.status == "sent"
                )
            )
            .values(
                status="read",
                read_at=datetime.utcnow()
            )
        )
        await self.db.commit()
        
        # 获取发送者ID列表（用于WebSocket通知）
        result = await self.db.execute(
            select(Message.sender_id)
            .where(
                and_(
                    Message.message_id.in_(message_ids),
                    Message.receiver_id == device_uuid
                )
            )
            .distinct()
        )
        sender_ids = [str(sid) for sid in result.scalars().all()]
        
        return {
            "updated_count": result.rowcount,
            "sender_ids": sender_ids,  # 用于WebSocket通知
        }
    
    async def _get_device(self, device_id: uuid.UUID) -> Optional[Device]:
        """根据ID获取设备"""
        result = await self.db.execute(
            select(Device).where(Device.device_id == device_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_or_create_session(
        self,
        user1_id: uuid.UUID,
        user2_id: uuid.UUID
    ) -> Session:
        """
        获取或创建会话
        
        确保user1_id < user2_id以避免重复会话
        """
        # 标准化用户ID顺序
        if user1_id > user2_id:
            user1_id, user2_id = user2_id, user1_id
        
        # 查找现有会话
        result = await self.db.execute(
            select(Session)
            .where(
                and_(
                    Session.user1_id == user1_id,
                    Session.user2_id == user2_id
                )
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # 检查是否过期
            if existing.is_expired():
                # 重新激活会话
                existing.expired_at = None
                await self.db.commit()
            return existing
        
        # 创建新会话
        new_session = Session(
            user1_id=user1_id,
            user2_id=user2_id,
            is_temp=True,
        )
        self.db.add(new_session)
        await self.db.commit()
        
        return new_session
    
    async def _check_temp_message_limit(
        self,
        session_id: uuid.UUID,
        sender_id: uuid.UUID,
        receiver_id: uuid.UUID
    ) -> bool:
        """
        检查临时消息限制
        
        规则：对方未回复前，发送者最多发送2条消息
        
        Returns:
            是否可以发送
        """
        # 统计发送者在此会话中的消息数
        result = await self.db.execute(
            select(func.count(Message.message_id))
            .where(
                and_(
                    Message.session_id == session_id,
                    Message.sender_id == sender_id
                )
            )
        )
        sender_count = result.scalar() or 0
        
        # 如果对方已经回复过，重置计数
        result = await self.db.execute(
            select(func.count(Message.message_id))
            .where(
                and_(
                    Message.session_id == session_id,
                    Message.sender_id == receiver_id
                )
            )
        )
        receiver_count = result.scalar() or 0
        
        # 如果对方回复过，允许继续发送
        if receiver_count > 0:
            return True
        
        # 检查是否超过限制
        return sender_count < self.TEMP_MESSAGE_LIMIT
