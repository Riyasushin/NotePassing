"""Relation service for managing friendships and blocks."""
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.friendship import Friendship
from app.models.block import Block
from app.models.device import Device
from app.models.session import Session
from app.schemas.friendship import (
    FriendItem,
    FriendListResponse,
    PendingFriendRequestItem,
    PendingFriendRequestListResponse,
    FriendRequestRequest,
    FriendRequestResponse,
    FriendResponseRequest,
    FriendInfo,
    FriendResponseResponse,
)
from app.schemas.block import BlockRequest
from app.services.websocket_manager import (
    push_friend_request,
    push_friend_response,
    push_friend_deleted,
)
from app.utils.validators import validate_device_id
from app.utils.exceptions import (
    DeviceNotInitializedError,
    BlockedByUserError,
    FriendRequestCooldownError,
    DuplicateOperationError,
    FriendshipNotExistError,
    InvalidParamsError,
)
from app.utils.uuid_utils import generate_uuid
from app.config import get_settings

settings = get_settings()


class RelationService:
    """Service for relation operations (friendship and block)."""

    @staticmethod
    async def get_pending_requests(
        db: AsyncSession,
        device_id: str,
    ) -> PendingFriendRequestListResponse:
        """Get incoming pending friend requests for a device."""
        validate_device_id(device_id)

        device_result = await db.execute(
            select(Device).where(Device.device_id == device_id)
        )
        if not device_result.scalar_one_or_none():
            raise DeviceNotInitializedError()

        result = await db.execute(
            select(Friendship, Device)
            .join(Device, Device.device_id == Friendship.sender_id)
            .where(
                Friendship.receiver_id == device_id,
                Friendship.status == "pending",
            )
            .order_by(Friendship.created_at.desc())
        )

        requests = [
            PendingFriendRequestItem(
                request_id=friendship.request_id,
                sender_id=sender.device_id,
                nickname=sender.nickname,
                avatar=sender.avatar,
                tags=sender.tags or [],
                message=friendship.message,
                created_at=friendship.created_at,
            )
            for friendship, sender in result.all()
        ]

        return PendingFriendRequestListResponse(requests=requests)
    
    @staticmethod
    async def get_friends(
        db: AsyncSession,
        device_id: str,
    ) -> FriendListResponse:
        """Get friend list for a device."""
        validate_device_id(device_id)

        device_result = await db.execute(
            select(Device).where(Device.device_id == device_id)
        )
        if not device_result.scalar_one_or_none():
            raise DeviceNotInitializedError()

        result = await db.execute(
            select(Friendship, Device).join(
                Device,
                or_(
                    and_(
                        Friendship.sender_id == device_id,
                        Device.device_id == Friendship.receiver_id,
                    ),
                    and_(
                        Friendship.receiver_id == device_id,
                        Device.device_id == Friendship.sender_id,
                    ),
                ),
            ).where(
                Friendship.status == "accepted",
            )
        )

        friends = []
        for friendship, friend_device in result.all():
            friend_id = friend_device.device_id
            a, b = (device_id, friend_id) if device_id < friend_id else (friend_id, device_id)

            sess_result = await db.execute(
                select(Session.last_message_at).where(
                    Session.device_a_id == a,
                    Session.device_b_id == b,
                )
            )
            last_chat_at = sess_result.scalar_one_or_none()

            friends.append(
                FriendItem(
                    device_id=friend_id,
                    nickname=friend_device.nickname,
                    avatar=friend_device.avatar,
                    tags=friend_device.tags or [],
                    profile=friend_device.profile,
                    is_anonymous=friend_device.is_anonymous,
                    last_chat_at=last_chat_at,
                )
            )

        return FriendListResponse(friends=friends)
    
    @staticmethod
    async def send_friend_request(
        db: AsyncSession,
        data: FriendRequestRequest,
    ) -> FriendRequestResponse:
        """
        Send a friend request.
        
        Args:
            db: Database session
            data: Friend request data
        
        Returns:
            Friend request response
        """
        validate_device_id(data.sender_id, "sender_id")
        validate_device_id(data.receiver_id, "receiver_id")
        
        # Check devices exist
        sender_result = await db.execute(
            select(Device).where(Device.device_id == data.sender_id)
        )
        sender = sender_result.scalar_one_or_none()
        if not sender:
            raise DeviceNotInitializedError()
        
        receiver_result = await db.execute(
            select(Device).where(Device.device_id == data.receiver_id)
        )
        if not receiver_result.scalar_one_or_none():
            raise DeviceNotInitializedError()
        
        # Check if sender is blocked by receiver
        block_result = await db.execute(
            select(Block).where(
                Block.device_id == data.receiver_id,
                Block.target_id == data.sender_id,
            )
        )
        if block_result.scalar_one_or_none():
            raise BlockedByUserError()
        
        # Check for existing friendship
        existing_result = await db.execute(
            select(Friendship).where(
                or_(
                    and_(
                        Friendship.sender_id == data.sender_id,
                        Friendship.receiver_id == data.receiver_id,
                    ),
                    and_(
                        Friendship.sender_id == data.receiver_id,
                        Friendship.receiver_id == data.sender_id,
                    ),
                ),
            )
        )
        existing = existing_result.scalar_one_or_none()
        
        if existing:
            if existing.status == "accepted":
                raise DuplicateOperationError()
            elif existing.status == "pending":
                raise DuplicateOperationError()
            elif existing.status == "rejected":
                # Check cooldown (24 hours)
                if existing.rejected_at:
                    cooldown_end = existing.rejected_at + timedelta(hours=24)
                    if datetime.utcnow() < cooldown_end:
                        raise FriendRequestCooldownError()
                
                # Allow re-request after cooldown - update existing record
                existing.status = "pending"
                existing.sender_id = data.sender_id
                existing.receiver_id = data.receiver_id
                existing.message = data.message
                existing.rejected_at = None
                existing.updated_at = datetime.utcnow()
                
                await db.flush()

                await push_friend_request(
                    data.receiver_id,
                    {
                        "request_id": existing.request_id,
                        "sender": {
                            "device_id": sender.device_id,
                            "nickname": sender.nickname,
                            "avatar": sender.avatar,
                            "tags": sender.tags or [],
                        },
                        "message": data.message,
                    },
                )
                
                return FriendRequestResponse(
                    request_id=existing.request_id,
                    status=existing.status,
                    created_at=existing.created_at,
                )
        
        # Create new friend request
        friendship = Friendship(
            request_id=generate_uuid(),
            sender_id=data.sender_id,
            receiver_id=data.receiver_id,
            status="pending",
            message=data.message,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(friendship)
        await db.flush()

        await push_friend_request(
            data.receiver_id,
            {
                "request_id": friendship.request_id,
                "sender": {
                    "device_id": sender.device_id,
                    "nickname": sender.nickname,
                    "avatar": sender.avatar,
                    "tags": sender.tags or [],
                },
                "message": data.message,
            },
        )
        
        return FriendRequestResponse(
            request_id=friendship.request_id,
            status=friendship.status,
            created_at=friendship.created_at,
        )
    
    @staticmethod
    async def respond_friend_request(
        db: AsyncSession,
        request_id: str,
        data: FriendResponseRequest,
    ) -> FriendResponseResponse:
        """
        Respond to a friend request (accept or reject).
        
        Args:
            db: Database session
            request_id: Request ID
            data: Response data with action
        
        Returns:
            Friend response response
        """
        validate_device_id(data.device_id)
        
        # Get the friend request
        result = await db.execute(
            select(Friendship).where(Friendship.request_id == request_id)
        )
        friendship = result.scalar_one_or_none()
        
        if not friendship:
            raise FriendshipNotExistError()
        
        # Verify the responder is the receiver
        if friendship.receiver_id != data.device_id:
            raise FriendshipNotExistError()
        
        if friendship.status != "pending":
            raise FriendshipNotExistError()
        
        if data.action == "accept":
            # Update friendship status
            friendship.status = "accepted"
            friendship.updated_at = datetime.utcnow()

            receiver_result = await db.execute(
                select(Device).where(Device.device_id == friendship.receiver_id)
            )
            receiver = receiver_result.scalar_one()
            
            # Get or create permanent session
            session = await RelationService._get_or_create_permanent_session(
                db, friendship.sender_id, friendship.receiver_id
            )
            
            # Get sender info
            sender_result = await db.execute(
                select(Device).where(Device.device_id == friendship.sender_id)
            )
            sender = sender_result.scalar_one()
            
            await db.flush()

            await push_friend_response(
                friendship.sender_id,
                {
                    "request_id": friendship.request_id,
                    "status": "accepted",
                    "friend": {
                        "device_id": receiver.device_id,
                        "nickname": receiver.nickname,
                    },
                    "session_id": session.session_id,
                },
            )
            
            return FriendResponseResponse(
                request_id=friendship.request_id,
                status="accepted",
                friend=FriendInfo(
                    device_id=sender.device_id,
                    nickname=sender.nickname,
                    avatar=sender.avatar,
                ),
                session_id=session.session_id,
            )
        
        else:  # reject
            friendship.status = "rejected"
            friendship.rejected_at = datetime.utcnow()
            friendship.updated_at = datetime.utcnow()
            
            await db.flush()

            await push_friend_response(
                friendship.sender_id,
                {
                    "request_id": friendship.request_id,
                    "status": "rejected",
                    "friend": None,
                    "session_id": None,
                },
            )
            
            return FriendResponseResponse(
                request_id=friendship.request_id,
                status="rejected",
            )
    
    @staticmethod
    async def delete_friend(
        db: AsyncSession,
        device_id: str,
        friend_device_id: str,
    ) -> None:
        """
        Delete a friendship.
        
        Args:
            db: Database session
            device_id: Device ID
            friend_device_id: Friend device ID
        """
        validate_device_id(device_id)
        validate_device_id(friend_device_id, "friend_device_id")
        
        # Find and delete friendship
        result = await db.execute(
            delete(Friendship).where(
                or_(
                    and_(
                        Friendship.sender_id == device_id,
                        Friendship.receiver_id == friend_device_id,
                    ),
                    and_(
                        Friendship.sender_id == friend_device_id,
                        Friendship.receiver_id == device_id,
                    ),
                ),
                Friendship.status == "accepted",
            )
        )
        
        if result.rowcount == 0:
            raise FriendshipNotExistError()

        await RelationService._expire_pair_session(db, device_id, friend_device_id)
        await db.flush()

        await push_friend_deleted(
            friend_device_id,
            {
                "peer_device_id": device_id,
            },
        )
    
    @staticmethod
    async def block_user(
        db: AsyncSession,
        data: BlockRequest,
    ) -> None:
        """
        Block a user.
        
        Args:
            db: Database session
            data: Block request with device_id and target_id
        """
        validate_device_id(data.device_id)
        validate_device_id(data.target_id, "target_id")
        
        # Check if already blocked
        existing_result = await db.execute(
            select(Block).where(
                Block.device_id == data.device_id,
                Block.target_id == data.target_id,
            )
        )
        if existing_result.scalar_one_or_none():
            raise DuplicateOperationError()
        
        # Create block
        block = Block(
            device_id=data.device_id,
            target_id=data.target_id,
            created_at=datetime.utcnow(),
        )
        db.add(block)
        
        # Delete any existing friendship
        await db.execute(
            delete(Friendship).where(
                or_(
                    and_(
                        Friendship.sender_id == data.device_id,
                        Friendship.receiver_id == data.target_id,
                    ),
                    and_(
                        Friendship.sender_id == data.target_id,
                        Friendship.receiver_id == data.device_id,
                    ),
                ),
            )
        )

        await RelationService._expire_pair_session(db, data.device_id, data.target_id)
        
        await db.flush()

        await push_friend_deleted(
            data.target_id,
            {
                "peer_device_id": data.device_id,
            },
        )
    
    @staticmethod
    async def unblock_user(
        db: AsyncSession,
        device_id: str,
        target_id: str,
    ) -> None:
        """
        Unblock a user.
        
        Args:
            db: Database session
            device_id: Device ID
            target_id: Target device ID
        """
        validate_device_id(device_id)
        validate_device_id(target_id, "target_id")
        
        result = await db.execute(
            delete(Block).where(
                Block.device_id == device_id,
                Block.target_id == target_id,
            )
        )
        
        if result.rowcount == 0:
            raise FriendshipNotExistError()  # Or a more specific error

    @staticmethod
    async def _expire_pair_session(
        db: AsyncSession,
        device_a: str,
        device_b: str,
    ) -> None:
        """Expire the current pair session so friendship removal takes effect immediately."""
        if device_a > device_b:
            device_a, device_b = device_b, device_a

        result = await db.execute(
            select(Session).where(
                Session.device_a_id == device_a,
                Session.device_b_id == device_b,
                Session.status == "active",
            )
        )
        session = result.scalar_one_or_none()

        if not session:
            return

        session.is_temp = True
        session.status = "expired"
        session.expires_at = datetime.utcnow()
    
    @staticmethod
    async def _get_or_create_permanent_session(
        db: AsyncSession,
        device_a: str,
        device_b: str,
    ) -> Session:
        """Get existing session or create a permanent one."""
        # Ensure consistent ordering
        if device_a > device_b:
            device_a, device_b = device_b, device_a
        
        # Try to find existing session
        result = await db.execute(
            select(Session).where(
                Session.device_a_id == device_a,
                Session.device_b_id == device_b,
            )
        )
        session = result.scalar_one_or_none()
        
        if session:
            # Upgrade to permanent if temp
            if session.is_temp:
                session.is_temp = False
                session.expires_at = None
            session.status = "active"
            return session
        
        # Create new permanent session
        session = Session(
            session_id=generate_uuid(),
            device_a_id=device_a,
            device_b_id=device_b,
            is_temp=False,
            status="active",
        )
        db.add(session)
        await db.flush()
        
        return session
