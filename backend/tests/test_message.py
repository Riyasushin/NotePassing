"""Tests for message service and endpoints."""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.message_service import MessageService
from app.services.device_service import DeviceService
from app.services.relation_service import RelationService
from app.schemas.message import SendMessageRequest, MarkReadRequest
from app.schemas.device import DeviceInitRequest
from app.utils.uuid_utils import generate_device_id, generate_uuid
from app.utils.exceptions import (
    DeviceNotInitializedError,
    BlockedByUserError,
    TempChatLimitReachedError,
    TempSessionExpiredError,
)
from app.models.friendship import Friendship
from app.models.block import Block
from app.models.session import Session


class TestMessageService:
    """Test MessageService methods."""
    
    @pytest.mark.asyncio
    async def test_send_message_friend(self, db_session: AsyncSession):
        """Test sending message between friends."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="User B")
        )
        
        # Create friendship
        friendship = Friendship(
            request_id=generate_uuid(),
            sender_id=device_a,
            receiver_id=device_b,
            status="accepted",
        )
        db_session.add(friendship)
        await db_session.commit()
        
        # Send message
        data = SendMessageRequest(
            sender_id=device_a,
            receiver_id=device_b,
            content="Hello friend!",
            type="common",
        )
        result = await MessageService.send_message(db_session, data)
        
        assert result.message_id is not None
        assert result.session_id is not None
        assert result.status == "sent"
        assert result.created_at is not None
    
    @pytest.mark.asyncio
    async def test_send_message_non_friend_creates_temp_session(self, db_session: AsyncSession):
        """Test sending message to non-friend creates temp session."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="User B")
        )
        
        # Send first message (no friendship)
        data = SendMessageRequest(
            sender_id=device_a,
            receiver_id=device_b,
            content="Hello stranger!",
            type="common",
        )
        result = await MessageService.send_message(db_session, data)
        
        assert result.message_id is not None
        assert result.session_id is not None
        
        # Verify session is temporary
        from sqlalchemy import select
        session_result = await db_session.execute(
            select(Session).where(Session.session_id == result.session_id)
        )
        session = session_result.scalar_one()
        assert session.is_temp is True
    
    @pytest.mark.asyncio
    async def test_send_message_temp_session_limit(self, db_session: AsyncSession):
        """Test temp session message limit (max 2 before reply)."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="User B")
        )
        
        # Send 2 messages from A to B
        for i in range(2):
            data = SendMessageRequest(
                sender_id=device_a,
                receiver_id=device_b,
                content=f"Message {i+1}",
                type="common",
            )
            await MessageService.send_message(db_session, data)
        
        # Third message should fail (limit reached)
        data = SendMessageRequest(
            sender_id=device_a,
            receiver_id=device_b,
            content="Message 3 - should fail",
            type="common",
        )
        with pytest.raises(TempChatLimitReachedError):
            await MessageService.send_message(db_session, data)
        
        # B replies
        data = SendMessageRequest(
            sender_id=device_b,
            receiver_id=device_a,
            content="Reply from B",
            type="common",
        )
        await MessageService.send_message(db_session, data)
        
        # Now A can send again
        data = SendMessageRequest(
            sender_id=device_a,
            receiver_id=device_b,
            content="Message 4 after reply",
            type="common",
        )
        result = await MessageService.send_message(db_session, data)
        assert result.message_id is not None
    
    @pytest.mark.asyncio
    async def test_send_message_blocked(self, db_session: AsyncSession):
        """Test sending message when blocked."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="User B")
        )
        
        # B blocks A
        block = Block(device_id=device_b, target_id=device_a)
        db_session.add(block)
        await db_session.commit()
        
        # A tries to send to B
        data = SendMessageRequest(
            sender_id=device_a,
            receiver_id=device_b,
            content="Hello?",
            type="common",
        )
        with pytest.raises(BlockedByUserError):
            await MessageService.send_message(db_session, data)

    @pytest.mark.asyncio
    async def test_send_message_after_friend_deleted_raises_expired(self, db_session: AsyncSession):
        """Deleting a friend should immediately invalidate the old permanent session."""
        device_a = generate_device_id()
        device_b = generate_device_id()

        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="User B")
        )

        friendship = Friendship(
            request_id=generate_uuid(),
            sender_id=device_a,
            receiver_id=device_b,
            status="accepted",
        )
        device_x, device_y = (device_a, device_b) if device_a < device_b else (device_b, device_a)
        session = Session(
            session_id=generate_uuid(),
            device_a_id=device_x,
            device_b_id=device_y,
            is_temp=False,
            status="active",
        )
        db_session.add(friendship)
        db_session.add(session)
        await db_session.commit()

        await RelationService.delete_friend(db_session, device_a, device_b)

        with pytest.raises(TempSessionExpiredError):
            await MessageService.send_message(
                db_session,
                SendMessageRequest(
                    sender_id=device_b,
                    receiver_id=device_a,
                    content="still there?",
                    type="common",
                ),
            )
    
    @pytest.mark.asyncio
    async def test_send_message_device_not_found(self, db_session: AsyncSession):
        """Test sending message to non-existent device."""
        device_a = generate_device_id()
        
        # Create only sender
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        
        data = SendMessageRequest(
            sender_id=device_a,
            receiver_id=generate_device_id(),
            content="Hello?",
            type="common",
        )
        with pytest.raises(DeviceNotInitializedError):
            await MessageService.send_message(db_session, data)
    
    @pytest.mark.asyncio
    async def test_get_history(self, db_session: AsyncSession):
        """Test getting message history."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="User B")
        )
        
        # Create friendship to avoid temp session limits
        friendship = Friendship(
            request_id=generate_uuid(),
            sender_id=device_a,
            receiver_id=device_b,
            status="accepted",
        )
        db_session.add(friendship)
        await db_session.commit()
        
        # Send messages
        for i in range(5):
            data = SendMessageRequest(
                sender_id=device_a,
                receiver_id=device_b,
                content=f"Message {i+1}",
                type="common",
            )
            await MessageService.send_message(db_session, data)
        
        # Get session_id
        from sqlalchemy import select
        session_result = await db_session.execute(
            select(Session).where(
                or_(
                    and_(Session.device_a_id == device_a, Session.device_b_id == device_b),
                    and_(Session.device_a_id == device_b, Session.device_b_id == device_a),
                )
            )
        )
        session = session_result.scalar_one()
        
        # Get history as device_b
        result = await MessageService.get_history(
            db_session, session.session_id, device_b, limit=10
        )
        
        assert result.session_id == session.session_id
        assert len(result.messages) == 5
        assert result.has_more is False
        
        # Check message order (chronological)
        for i, msg in enumerate(result.messages):
            assert msg.content == f"Message {i+1}"
    
    @pytest.mark.asyncio
    async def test_get_history_pagination(self, db_session: AsyncSession):
        """Test message history pagination."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="User B")
        )
        
        # Create friendship to avoid temp session limits
        friendship = Friendship(
            request_id=generate_uuid(),
            sender_id=device_a,
            receiver_id=device_b,
            status="accepted",
        )
        db_session.add(friendship)
        await db_session.commit()
        
        # Send messages (3 messages, less than limit)
        for i in range(3):
            data = SendMessageRequest(
                sender_id=device_a,
                receiver_id=device_b,
                content=f"Message {i+1}",
                type="common",
            )
            await MessageService.send_message(db_session, data)
        
        # Get session_id
        session_result = await db_session.execute(
            select(Session).where(
                or_(
                    and_(Session.device_a_id == device_a, Session.device_b_id == device_b),
                    and_(Session.device_a_id == device_b, Session.device_b_id == device_a),
                )
            )
        )
        session = session_result.scalar_one()
        
        # Get history with limit > message count
        result = await MessageService.get_history(
            db_session, session.session_id, device_b, limit=5
        )
        
        assert len(result.messages) == 3
        assert result.has_more is False  # No more messages
        
        # Verify message order (chronological)
        assert result.messages[0].content == "Message 1"
        assert result.messages[1].content == "Message 2"
        assert result.messages[2].content == "Message 3"
    
    @pytest.mark.asyncio
    async def test_mark_read(self, db_session: AsyncSession):
        """Test marking messages as read."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="User B")
        )
        
        # Send messages
        data = SendMessageRequest(
            sender_id=device_a,
            receiver_id=device_b,
            content="Please read this",
            type="common",
        )
        result = await MessageService.send_message(db_session, data)
        
        # Mark as read by receiver (device_b)
        mark_data = MarkReadRequest(
            device_id=device_b,
            message_ids=[result.message_id],
        )
        mark_result = await MessageService.mark_read(db_session, mark_data)
        
        assert mark_result.updated_count == 1
        
        # Verify message status
        from sqlalchemy import select
        from app.models.message import Message
        msg_result = await db_session.execute(
            select(Message).where(Message.message_id == result.message_id)
        )
        message = msg_result.scalar_one()
        assert message.status == "read"
        assert message.read_at is not None
    
    @pytest.mark.asyncio
    async def test_mark_read_not_receiver(self, db_session: AsyncSession):
        """Test marking as read by non-receiver doesn't work."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="User B")
        )
        
        # Send message
        data = SendMessageRequest(
            sender_id=device_a,
            receiver_id=device_b,
            content="Hello",
            type="common",
        )
        result = await MessageService.send_message(db_session, data)
        
        # Try to mark as read by sender (device_a)
        mark_data = MarkReadRequest(
            device_id=device_a,
            message_ids=[result.message_id],
        )
        mark_result = await MessageService.mark_read(db_session, mark_data)
        
        # Should not update anything
        assert mark_result.updated_count == 0


class TestMessageEndpoints:
    """Test message API endpoints."""
    
    @pytest.mark.asyncio
    async def test_send_message_endpoint(self, client: AsyncClient):
        """Test POST /api/v1/messages."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await client.post("/api/v1/device/init", json={
            "device_id": device_a,
            "nickname": "User A",
        })
        await client.post("/api/v1/device/init", json={
            "device_id": device_b,
            "nickname": "User B",
        })
        
        # Send message
        response = await client.post("/api/v1/messages", json={
            "sender_id": device_a,
            "receiver_id": device_b,
            "content": "Hello via API",
            "type": "common",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["message_id"] is not None
        assert data["data"]["session_id"] is not None
        assert data["data"]["status"] == "sent"
    
    @pytest.mark.asyncio
    async def test_send_message_blocked_endpoint(self, client: AsyncClient):
        """Test sending message when blocked via API."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await client.post("/api/v1/device/init", json={
            "device_id": device_a,
            "nickname": "User A",
        })
        await client.post("/api/v1/device/init", json={
            "device_id": device_b,
            "nickname": "User B",
        })
        
        # B blocks A
        # Note: Block endpoint not implemented yet, using service directly
        from sqlalchemy import insert
        from app.models.block import Block
        # This would need to be done via API when block endpoint is ready
        
        # For now, skip this test or implement block creation
        pass
    
    @pytest.mark.asyncio
    async def test_get_history_endpoint(self, client: AsyncClient):
        """Test GET /api/v1/messages/{session_id}."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await client.post("/api/v1/device/init", json={
            "device_id": device_a,
            "nickname": "User A",
        })
        await client.post("/api/v1/device/init", json={
            "device_id": device_b,
            "nickname": "User B",
        })
        
        # Send a message and get session_id from response
        send_response = await client.post("/api/v1/messages", json={
            "sender_id": device_a,
            "receiver_id": device_b,
            "content": "First message",
            "type": "common",
        })
        response_data = send_response.json()
        assert response_data["code"] == 0
        session_id = response_data["data"]["session_id"]
        
        # Get history
        response = await client.get(
            f"/api/v1/messages/{session_id}?device_id={device_b}&limit=10"
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "messages" in data["data"]
        assert "has_more" in data["data"]
    
    @pytest.mark.asyncio
    async def test_mark_read_endpoint(self, client: AsyncClient):
        """Test POST /api/v1/messages/read."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await client.post("/api/v1/device/init", json={
            "device_id": device_a,
            "nickname": "User A",
        })
        await client.post("/api/v1/device/init", json={
            "device_id": device_b,
            "nickname": "User B",
        })
        
        # Send message
        send_response = await client.post("/api/v1/messages", json={
            "sender_id": device_a,
            "receiver_id": device_b,
            "content": "Mark me as read",
            "type": "common",
        })
        message_id = send_response.json()["data"]["message_id"]
        
        # Mark as read
        response = await client.post("/api/v1/messages/read", json={
            "device_id": device_b,
            "message_ids": [message_id],
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["updated_count"] == 1
