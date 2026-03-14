"""
关系服务 - 处理好友关系和屏蔽关系
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, List

from sqlalchemy import select, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Friendship, Block, Device, Session
from app.schemas import (
    SendFriendRequest,
    RespondFriendRequest,
    BlockUserRequest,
)
from app.utils import is_valid_uuid
from app.exceptions import (
    ValidationError,
    DeviceNotInitializedError,
    FriendshipNotFoundError,
    DuplicateOperationError,
    BlockedError,
    CooldownError,
)


class RelationService:
    """关系服务类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_friends_list(self, device_id: str) -> List[dict]:
        """
        获取好友列表
        
        Args:
            device_id: 设备ID
            
        Returns:
            好友列表，按最后聊天时间排序
        """
        if not is_valid_uuid(device_id):
            raise ValidationError("device_id格式错误")
        
        device_uuid = uuid.UUID(device_id)
        
        # 查询所有 accepted 状态的好友关系
        result = await self.db.execute(
            select(Friendship, Device)
            .join(Device, 
                or_(
                    and_(Friendship.friend_id == Device.device_id, Friendship.user_id == device_uuid),
                    and_(Friendship.user_id == Device.device_id, Friendship.friend_id == device_uuid)
                )
            )
            .where(
                and_(
                    or_(Friendship.user_id == device_uuid, Friendship.friend_id == device_uuid),
                    Friendship.status == "accepted"
                )
            )
        )
        
        friends = []
        for friendship, friend_device in result.all():
            # 确定好友ID（非当前用户的那个）
            if friendship.user_id == device_uuid:
                friend_id = friendship.friend_id
            else:
                friend_id = friendship.user_id
            
            # 获取最后聊天时间
            last_chat_at = await self._get_last_chat_time(device_uuid, friend_id)
            
            friends.append({
                "device_id": str(friend_device.device_id),
                "nickname": friend_device.nickname,
                "avatar": friend_device.avatar,
                "tags": friend_device.tags or [],
                "profile": friend_device.profile or "",
                "is_anonymous": friend_device.is_anonymous,
                "last_chat_at": last_chat_at.isoformat() if last_chat_at else None,
            })
        
        # 按最后聊天时间排序（降序）
        friends.sort(
            key=lambda x: x["last_chat_at"] or "",
            reverse=True
        )
        
        return friends
    
    async def send_friend_request(
        self,
        request: SendFriendRequest
    ) -> dict:
        """
        发送好友申请
        
        Args:
            request: 好友申请请求
            
        Returns:
            申请信息
        """
        # 验证ID
        if not is_valid_uuid(request.sender_id):
            raise ValidationError("sender_id格式错误")
        if not is_valid_uuid(request.receiver_id):
            raise ValidationError("receiver_id格式错误")
        
        sender_uuid = uuid.UUID(request.sender_id)
        receiver_uuid = uuid.UUID(request.receiver_id)
        
        # 不能向自己发送申请
        if sender_uuid == receiver_uuid:
            raise ValidationError("不能向自己发送好友申请")
        
        # 检查是否被屏蔽
        is_blocked = await self._is_blocked(request.receiver_id, request.sender_id)
        if is_blocked:
            raise BlockedError()
        
        # 检查是否已经是好友
        is_friend = await self.check_friendship(
            request.sender_id,
            request.receiver_id
        )
        if is_friend:
            raise DuplicateOperationError()
        
        # 检查是否已有待处理申请
        existing = await self.db.execute(
            select(Friendship)
            .where(
                and_(
                    Friendship.user_id == sender_uuid,
                    Friendship.friend_id == receiver_uuid,
                    Friendship.status == "pending"
                )
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateOperationError()
        
        # 检查是否被拒绝过（冷却期检查）
        rejected = await self.db.execute(
            select(Friendship)
            .where(
                and_(
                    Friendship.user_id == sender_uuid,
                    Friendship.friend_id == receiver_uuid,
                    Friendship.status == "rejected"
                )
            )
            .order_by(Friendship.updated_at.desc())
        )
        rejected_record = rejected.scalar_one_or_none()
        
        if rejected_record and rejected_record.is_in_cooldown():
            raise CooldownError()
        
        # 如果之前有拒绝记录，删除它（重新申请）
        if rejected_record:
            await self.db.delete(rejected_record)
        
        # 创建新的好友申请
        friendship = Friendship(
            user_id=sender_uuid,
            friend_id=receiver_uuid,
            status="pending",
            message=request.message,
        )
        self.db.add(friendship)
        await self.db.commit()
        
        return {
            "request_id": str(friendship.request_id),
            "status": friendship.status,
            "created_at": friendship.created_at.isoformat(),
        }
    
    async def respond_friend_request(
        self,
        request_id: str,
        request: RespondFriendRequest
    ) -> dict:
        """
        回应好友申请
        
        Args:
            request_id: 申请ID
            request: 回应请求
            
        Returns:
            回应结果
        """
        if not is_valid_uuid(request_id):
            raise ValidationError("request_id格式错误")
        if not is_valid_uuid(request.device_id):
            raise ValidationError("device_id格式错误")
        
        request_uuid = uuid.UUID(request_id)
        device_uuid = uuid.UUID(request.device_id)
        
        # 查询申请
        result = await self.db.execute(
            select(Friendship)
            .where(
                and_(
                    Friendship.request_id == request_uuid,
                    Friendship.friend_id == device_uuid,
                    Friendship.status == "pending"
                )
            )
        )
        friendship = result.scalar_one_or_none()
        
        if not friendship:
            raise FriendshipNotFoundError()
        
        action = request.action.lower()
        
        if action == "accept":
            # 接受申请
            friendship.status = "accepted"
            friendship.updated_at = datetime.utcnow()
            await self.db.commit()
            
            # 创建或升级为永久会话
            session_id = await self._create_or_upgrade_session(
                str(friendship.user_id),
                str(friendship.friend_id)
            )
            
            # 获取好友信息
            result = await self.db.execute(
                select(Device).where(Device.device_id == friendship.user_id)
            )
            friend = result.scalar_one()
            
            return {
                "request_id": str(friendship.request_id),
                "status": "accepted",
                "friend": {
                    "device_id": str(friend.device_id),
                    "nickname": friend.nickname,
                    "avatar": friend.avatar,
                },
                "session_id": session_id,
            }
        
        elif action == "reject":
            # 拒绝申请
            friendship.status = "rejected"
            friendship.updated_at = datetime.utcnow()
            await self.db.commit()
            
            return {
                "request_id": str(friendship.request_id),
                "status": "rejected",
            }
        
        else:
            raise ValidationError("action必须是accept或reject")
    
    async def delete_friend(
        self,
        device_id: str,
        friend_device_id: str
    ) -> None:
        """
        删除好友
        
        Args:
            device_id: 操作者设备ID
            friend_device_id: 好友设备ID
        """
        if not is_valid_uuid(device_id) or not is_valid_uuid(friend_device_id):
            raise ValidationError("device_id格式错误")
        
        device_uuid = uuid.UUID(device_id)
        friend_uuid = uuid.UUID(friend_device_id)
        
        # 删除好友关系
        await self.db.execute(
            delete(Friendship)
            .where(
                or_(
                    and_(
                        Friendship.user_id == device_uuid,
                        Friendship.friend_id == friend_uuid,
                        Friendship.status == "accepted"
                    ),
                    and_(
                        Friendship.user_id == friend_uuid,
                        Friendship.friend_id == device_uuid,
                        Friendship.status == "accepted"
                    )
                )
            )
        )
        
        # 降级会话为临时会话
        await self.db.execute(
            update(Session)
            .where(
                or_(
                    and_(Session.user1_id == device_uuid, Session.user2_id == friend_uuid),
                    and_(Session.user1_id == friend_uuid, Session.user2_id == device_uuid)
                )
            )
            .values(is_temp=True)
        )
        
        await self.db.commit()
    
    async def block_user(self, request: BlockUserRequest) -> None:
        """
        屏蔽用户
        
        Args:
            request: 屏蔽请求
        """
        if not is_valid_uuid(request.device_id):
            raise ValidationError("device_id格式错误")
        if not is_valid_uuid(request.target_id):
            raise ValidationError("target_id格式错误")
        
        blocker_uuid = uuid.UUID(request.device_id)
        target_uuid = uuid.UUID(request.target_id)
        
        if blocker_uuid == target_uuid:
            raise ValidationError("不能屏蔽自己")
        
        # 删除好友关系（如果存在）
        await self.db.execute(
            delete(Friendship)
            .where(
                or_(
                    and_(
                        Friendship.user_id == blocker_uuid,
                        Friendship.friend_id == target_uuid
                    ),
                    and_(
                        Friendship.user_id == target_uuid,
                        Friendship.friend_id == blocker_uuid
                    )
                )
            )
        )
        
        # 添加屏蔽记录
        # 先检查是否已存在
        result = await self.db.execute(
            select(Block)
            .where(
                and_(
                    Block.blocker_id == blocker_uuid,
                    Block.target_id == target_uuid
                )
            )
        )
        if not result.scalar_one_or_none():
            block = Block(
                blocker_id=blocker_uuid,
                target_id=target_uuid,
            )
            self.db.add(block)
        
        # 删除附近关系记录
        from app.models import Presence
        await self.db.execute(
            delete(Presence)
            .where(
                or_(
                    and_(
                        Presence.user_id == blocker_uuid,
                        Presence.nearby_user_id == target_uuid
                    ),
                    and_(
                        Presence.user_id == target_uuid,
                        Presence.nearby_user_id == blocker_uuid
                    )
                )
            )
        )
        
        await self.db.commit()
    
    async def unblock_user(self, device_id: str, target_id: str) -> None:
        """
        取消屏蔽用户
        
        Args:
            device_id: 操作者设备ID
            target_id: 目标设备ID
        """
        if not is_valid_uuid(device_id) or not is_valid_uuid(target_id):
            raise ValidationError("device_id格式错误")
        
        blocker_uuid = uuid.UUID(device_id)
        target_uuid = uuid.UUID(target_id)
        
        await self.db.execute(
            delete(Block)
            .where(
                and_(
                    Block.blocker_id == blocker_uuid,
                    Block.target_id == target_uuid
                )
            )
        )
        await self.db.commit()
    
    async def check_friendship(
        self,
        device_id1: str,
        device_id2: str
    ) -> bool:
        """
        检查两个用户是否为好友
        
        Args:
            device_id1: 用户1 ID
            device_id2: 用户2 ID
            
        Returns:
            是否为好友
        """
        if not is_valid_uuid(device_id1) or not is_valid_uuid(device_id2):
            return False
        
        uuid1 = uuid.UUID(device_id1)
        uuid2 = uuid.UUID(device_id2)
        
        result = await self.db.execute(
            select(Friendship)
            .where(
                or_(
                    and_(
                        Friendship.user_id == uuid1,
                        Friendship.friend_id == uuid2,
                        Friendship.status == "accepted"
                    ),
                    and_(
                        Friendship.user_id == uuid2,
                        Friendship.friend_id == uuid1,
                        Friendship.status == "accepted"
                    )
                )
            )
        )
        
        return result.scalar_one_or_none() is not None
    
    async def _is_blocked(
        self,
        blocker_id: str,
        target_id: str
    ) -> bool:
        """
        检查是否被屏蔽
        
        Args:
            blocker_id: 可能屏蔽他人的用户ID
            target_id: 可能被屏蔽的用户ID
            
        Returns:
            是否被屏蔽
        """
        if not is_valid_uuid(blocker_id) or not is_valid_uuid(target_id):
            return False
        
        blocker_uuid = uuid.UUID(blocker_id)
        target_uuid = uuid.UUID(target_id)
        
        result = await self.db.execute(
            select(Block)
            .where(
                and_(
                    Block.blocker_id == blocker_uuid,
                    Block.target_id == target_uuid
                )
            )
        )
        
        return result.scalar_one_or_none() is not None
    
    async def get_blocked_users(self, device_id: str) -> List[str]:
        """
        获取用户屏蔽的所有人
        
        Returns:
            被屏蔽用户的ID列表
        """
        if not is_valid_uuid(device_id):
            return []
        
        device_uuid = uuid.UUID(device_id)
        
        result = await self.db.execute(
            select(Block.target_id)
            .where(Block.blocker_id == device_uuid)
        )
        
        return [str(tid) for tid in result.scalars().all()]
    
    async def get_blocking_users(self, device_id: str) -> List[str]:
        """
        获取屏蔽该用户的所有人
        
        Returns:
            屏蔽者的ID列表
        """
        if not is_valid_uuid(device_id):
            return []
        
        device_uuid = uuid.UUID(device_id)
        
        result = await self.db.execute(
            select(Block.blocker_id)
            .where(Block.target_id == device_uuid)
        )
        
        return [str(bid) for bid in result.scalars().all()]
    
    async def _get_last_chat_time(
        self,
        user1_id: uuid.UUID,
        user2_id: uuid.UUID
    ) -> Optional[datetime]:
        """获取两个用户最后聊天时间"""
        from app.models import Message
        
        result = await self.db.execute(
            select(Message.created_at)
            .where(
                or_(
                    and_(
                        Message.sender_id == user1_id,
                        Message.receiver_id == user2_id
                    ),
                    and_(
                        Message.sender_id == user2_id,
                        Message.receiver_id == user1_id
                    )
                )
            )
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        
        return result.scalar_one_or_none()
    
    async def _create_or_upgrade_session(
        self,
        user1_id: str,
        user2_id: str
    ) -> str:
        """
        创建或升级会话为永久会话
        
        Returns:
            会话ID
        """
        uuid1 = uuid.UUID(user1_id)
        uuid2 = uuid.UUID(user2_id)
        
        # 查找现有会话
        result = await self.db.execute(
            select(Session)
            .where(
                or_(
                    and_(Session.user1_id == uuid1, Session.user2_id == uuid2),
                    and_(Session.user1_id == uuid2, Session.user2_id == uuid1)
                )
            )
        )
        existing_session = result.scalar_one_or_none()
        
        if existing_session:
            # 升级为永久会话
            existing_session.is_temp = False
            existing_session.expired_at = None
            await self.db.commit()
            return str(existing_session.session_id)
        else:
            # 创建新永久会话
            new_session = Session(
                user1_id=uuid1,
                user2_id=uuid2,
                is_temp=False,
            )
            self.db.add(new_session)
            await self.db.commit()
            return str(new_session.session_id)
