"""Message service for managing chat messages."""
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import select, update, desc, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message
from app.models.session import Session
from app.models.device import Device
from app.models.friendship import Friendship
from app.models.block import Block
from app.schemas.message import (
    SendMessageRequest,
    SendMessageResponse,
    MessageHistoryItem,
    MessageHistoryResponse,
    MarkReadRequest,
    MarkReadResponse,
)
from app.utils.validators import validate_device_id, validate_content
from app.utils.exceptions import (
    DeviceNotInitializedError,
    BlockedByUserError,
    TempChatLimitReachedError,
    TempSessionExpiredError,
    FriendshipNotExistError,
    InvalidParamsError,
)
from app.utils.uuid_utils import generate_uuid
from app.config import get_settings

settings = get_settings()


class MessageService:
    """Service for message operations."""
    
    @staticmethod
    async def send_message(
        db: AsyncSession,
        data: SendMessageRequest,
    ) -> SendMessageResponse:
        """
        Send a message from sender to receiver.
        
        Args:
            db: Database session
            data: Send message request
        
        Returns:
            Send message response with message_id and session_id
        """
        # Validate inputs
        validate_device_id(data.sender_id, "sender_id")
        validate_device_id(data.receiver_id, "receiver_id")
        validate_content(data.content)
        
        # Check if sender exists
        sender_result = await db.execute(
            select(Device).where(Device.device_id == data.sender_id)
        )
        sender = sender_result.scalar_one_or_none()
        if not sender:
            raise DeviceNotInitializedError()
        
        # Check if receiver exists
        receiver_result = await db.execute(
            select(Device).where(Device.device_id == data.receiver_id)
        )
        receiver = receiver_result.scalar_one_or_none()
        if not receiver:
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
        
        # Check friendship status
        is_friend = await MessageService._check_friendship(
            db, data.sender_id, data.receiver_id
        )
        
        # Get or create session
        session = await MessageService._get_or_create_session(
            db, data.sender_id, data.receiver_id, is_friend
        )
        
        # For temp sessions, check message limit (max 2 messages before reply)
        if session.is_temp:
            can_send = await MessageService._check_temp_session_limit(
                db, session.session_id, data.sender_id
            )
            if not can_send:
                raise TempChatLimitReachedError()
        
        # Create message
        message = Message(
            message_id=generate_uuid(),
            session_id=session.session_id,
            sender_id=data.sender_id,
            receiver_id=data.receiver_id,
            content=data.content,
            type=data.type,
            status="sent",
            created_at=datetime.utcnow(),
        )
        db.add(message)
        
        # Update session last_message_at
        session.last_message_at = datetime.utcnow()
        
        await db.flush()
        
        return SendMessageResponse(
            message_id=message.message_id,
            session_id=session.session_id,
            status=message.status,
            created_at=message.created_at,
        )
    
    @staticmethod
    async def get_history(
        db: AsyncSession,
        session_id: str,
        device_id: str,
        before: Optional[datetime] = None,
        limit: int = 20,
    ) -> MessageHistoryResponse:
        """
        Get message history for a session.
        
        Args:
            db: Database session
            session_id: Session ID
            device_id: Requester device ID (for permission check)
            before: Get messages before this time (for pagination)
            limit: Maximum number of messages to return
        
        Returns:
            Message history response
        """
        validate_device_id(device_id)
        
        if limit > 50:
            limit = 50
        
        # Check if session exists and device is a participant
        session_result = await db.execute(
            select(Session).where(
                Session.session_id == session_id,
                or_(
                    Session.device_a_id == device_id,
                    Session.device_b_id == device_id,
                ),
            )
        )
        session = session_result.scalar_one_or_none()
        
        if not session:
            raise FriendshipNotExistError()  # Or a more specific error
        
        # Build query
        query = select(Message).where(
            Message.session_id == session_id
        ).order_by(desc(Message.created_at))
        
        if before:
            query = query.where(Message.created_at < before)
        
        query = query.limit(limit + 1)  # +1 to check if there are more
        
        result = await db.execute(query)
        messages = result.scalars().all()
        
        # Check if there are more messages
        has_more = len(messages) > limit
        messages = list(messages[:limit])
        
        # Convert to response items
        message_items = [
            MessageHistoryItem(
                message_id=msg.message_id,
                sender_id=msg.sender_id,
                content=msg.content,
                type=msg.type,
                status=msg.status,
                created_at=msg.created_at,
            )
            for msg in reversed(messages)  # Return in chronological order
        ]
        
        return MessageHistoryResponse(
            session_id=session_id,
            messages=message_items,
            has_more=has_more,
        )
    
    @staticmethod
    async def mark_read(
        db: AsyncSession,
        data: MarkReadRequest,
    ) -> MarkReadResponse:
        """
        Mark messages as read.
        
        Args:
            db: Database session
            data: Mark read request with device_id and message_ids
        
        Returns:
            Mark read response with updated count
        """
        validate_device_id(data.device_id)
        
        if not data.message_ids:
            return MarkReadResponse(updated_count=0)
        
        # Update messages where the requester is the receiver
        result = await db.execute(
            update(Message)
            .where(
                Message.message_id.in_(data.message_ids),
                Message.receiver_id == data.device_id,
                Message.status != "read",
            )
            .values(
                status="read",
                read_at=datetime.utcnow(),
            )
        )
        
        return MarkReadResponse(updated_count=result.rowcount)
    
    @staticmethod
    async def _check_friendship(
        db: AsyncSession,
        device_a: str,
        device_b: str,
    ) -> bool:
        """Check if two devices are friends."""
        result = await db.execute(
            select(Friendship).where(
                or_(
                    and_(
                        Friendship.sender_id == device_a,
                        Friendship.receiver_id == device_b,
                    ),
                    and_(
                        Friendship.sender_id == device_b,
                        Friendship.receiver_id == device_a,
                    ),
                ),
                Friendship.status == "accepted",
            )
        )
        return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def _get_or_create_session(
        db: AsyncSession,
        device_a: str,
        device_b: str,
        is_friend: bool,
    ) -> Session:
        """Get existing session or create a new one."""
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
            # Check if temp session is expired
            if session.is_temp and session.is_expired():
                raise TempSessionExpiredError()
            return session
        
        # Create new session
        session = Session(
            session_id=generate_uuid(),
            device_a_id=device_a,
            device_b_id=device_b,
            is_temp=not is_friend,
            status="active",
            expires_at=datetime.utcnow() + timedelta(hours=1) if not is_friend else None,
        )
        db.add(session)
        await db.flush()
        
        return session
    
    @staticmethod
    async def _check_temp_session_limit(
        db: AsyncSession,
        session_id: str,
        sender_id: str,
    ) -> bool:
        """
        Check if sender can send message in temp session.
        Returns True if can send, False if limit reached (max 2 messages before reply).
        """
        # Count messages sent by sender in this session
        result = await db.execute(
            select(func.count(Message.message_id)).where(
                Message.session_id == session_id,
                Message.sender_id == sender_id,
            )
        )
        sender_message_count = result.scalar() or 0
        
        # If sender has sent less than 2 messages, they can send
        # If they sent 2 or more, they need to wait for a reply
        if sender_message_count < 2:
            return True
        
        # Check if receiver has replied
        result = await db.execute(
            select(func.count(Message.message_id)).where(
                Message.session_id == session_id,
                Message.sender_id != sender_id,
            )
        )
        receiver_message_count = result.scalar() or 0
        
        # Can send if receiver has replied
        return receiver_message_count > 0
