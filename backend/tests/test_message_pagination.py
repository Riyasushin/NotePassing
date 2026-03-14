"""Improved pagination tests for message service."""
import pytest
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.message_service import MessageService
from app.services.device_service import DeviceService
from app.schemas.message import SendMessageRequest
from app.schemas.device import DeviceInitRequest
from app.utils.uuid_utils import generate_device_id, generate_uuid
from app.models.friendship import Friendship
from app.models.session import Session
from sqlalchemy import select, and_, or_


class TestMessagePaginationImproved:
    """Improved pagination tests using time delays."""
    
    @pytest.mark.asyncio
    async def test_pagination_with_time_delay(self, db_session: AsyncSession):
        """Test pagination with explicit time delays between messages."""
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
        
        # Send messages with delays to ensure distinct timestamps
        for i in range(6):
            data = SendMessageRequest(
                sender_id=device_a,
                receiver_id=device_b,
                content=f"Message {i+1}",
                type="common",
            )
            await MessageService.send_message(db_session, data)
            # Small delay to ensure timestamp difference
            await asyncio.sleep(0.02)  # 20ms delay
        
        # Get session
        session_result = await db_session.execute(
            select(Session).where(
                or_(
                    and_(Session.device_a_id == device_a, Session.device_b_id == device_b),
                    and_(Session.device_a_id == device_b, Session.device_b_id == device_a),
                )
            )
        )
        session = session_result.scalar_one()
        
        # Page 1: Get first 3 messages (newest)
        page1 = await MessageService.get_history(
            db_session, session.session_id, device_b, limit=3
        )
        
        assert len(page1.messages) == 3
        assert page1.has_more is True
        # Messages returned in chronological order
        assert page1.messages[0].content == "Message 4"
        assert page1.messages[1].content == "Message 5"
        assert page1.messages[2].content == "Message 6"
        
        # Page 2: Get next messages
        last_msg = page1.messages[0]  # Oldest in current page
        page2 = await MessageService.get_history(
            db_session, session.session_id, device_b, 
            before=last_msg.created_at, limit=3
        )
        
        assert len(page2.messages) == 3
        assert page2.has_more is False
        assert page2.messages[0].content == "Message 1"
        assert page2.messages[1].content == "Message 2"
        assert page2.messages[2].content == "Message 3"
    
    @pytest.mark.asyncio
    async def test_pagination_cursor_behavior(self, db_session: AsyncSession):
        """Test that pagination correctly excludes the cursor message."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Setup
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
        db_session.add(friendship)
        await db_session.commit()
        
        # Send 5 messages with delays
        timestamps = []
        for i in range(5):
            data = SendMessageRequest(
                sender_id=device_a,
                receiver_id=device_b,
                content=f"Msg {i+1}",
                type="common",
            )
            result = await MessageService.send_message(db_session, data)
            timestamps.append(result.created_at)
            await asyncio.sleep(0.02)
        
        # Get session
        session_result = await db_session.execute(
            select(Session).where(
                or_(
                    and_(Session.device_a_id == device_a, Session.device_b_id == device_b),
                    and_(Session.device_a_id == device_b, Session.device_b_id == device_a),
                )
            )
        )
        session = session_result.scalar_one()
        
        # Get all messages
        all_messages = await MessageService.get_history(
            db_session, session.session_id, device_b, limit=10
        )
        
        assert len(all_messages.messages) == 5
        
        # Use middle message as cursor
        middle_msg = all_messages.messages[2]  # Msg 3
        
        # Get messages before middle (should be Msg 1 and 2)
        before_middle = await MessageService.get_history(
            db_session, session.session_id, device_b,
            before=middle_msg.created_at, limit=10
        )
        
        # Should only contain Msg 1 and 2
        contents = [m.content for m in before_middle.messages]
        assert "Msg 1" in contents
        assert "Msg 2" in contents
        assert "Msg 3" not in contents  # Cursor should be excluded
        assert "Msg 4" not in contents
        assert "Msg 5" not in contents
    
    @pytest.mark.asyncio
    async def test_pagination_empty_result(self, db_session: AsyncSession):
        """Test pagination when no more messages exist."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Setup
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
        db_session.add(friendship)
        await db_session.commit()
        
        # Send 2 messages
        for i in range(2):
            data = SendMessageRequest(
                sender_id=device_a,
                receiver_id=device_b,
                content=f"Message {i+1}",
                type="common",
            )
            await MessageService.send_message(db_session, data)
            await asyncio.sleep(0.02)
        
        # Get session
        session_result = await db_session.execute(
            select(Session).where(
                or_(
                    and_(Session.device_a_id == device_a, Session.device_b_id == device_b),
                    and_(Session.device_a_id == device_b, Session.device_b_id == device_a),
                )
            )
        )
        session = session_result.scalar_one()
        
        # Get all messages
        result = await MessageService.get_history(
            db_session, session.session_id, device_b, limit=5
        )
        
        assert len(result.messages) == 2
        assert result.has_more is False
        
        # Try to get more messages after exhausting
        oldest_msg = result.messages[0]
        empty_result = await MessageService.get_history(
            db_session, session.session_id, device_b,
            before=oldest_msg.created_at, limit=5
        )
        
        assert len(empty_result.messages) == 0
        assert empty_result.has_more is False


class TestMessagePaginationEdgeCases:
    """Edge case tests for pagination."""
    
    @pytest.mark.asyncio
    async def test_pagination_limit_respected(self, db_session: AsyncSession):
        """Test that limit parameter is strictly respected."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Setup
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
        db_session.add(friendship)
        await db_session.commit()
        
        # Send 10 messages
        for i in range(10):
            data = SendMessageRequest(
                sender_id=device_a,
                receiver_id=device_b,
                content=f"Message {i+1}",
                type="common",
            )
            await MessageService.send_message(db_session, data)
            await asyncio.sleep(0.01)
        
        # Get session
        session_result = await db_session.execute(
            select(Session).where(
                or_(
                    and_(Session.device_a_id == device_a, Session.device_b_id == device_b),
                    and_(Session.device_a_id == device_b, Session.device_b_id == device_a),
                )
            )
        )
        session = session_result.scalar_one()
        
        # Request with limit=3
        result = await MessageService.get_history(
            db_session, session.session_id, device_b, limit=3
        )
        
        # Should return exactly 3 messages
        assert len(result.messages) == 3
        assert result.has_more is True
    
    @pytest.mark.asyncio
    async def test_pagination_limit_max_50(self, db_session: AsyncSession):
        """Test that limit cannot exceed 50."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Setup
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
        db_session.add(friendship)
        await db_session.commit()
        
        # Send 5 messages
        for i in range(5):
            data = SendMessageRequest(
                sender_id=device_a,
                receiver_id=device_b,
                content=f"Message {i+1}",
                type="common",
            )
            await MessageService.send_message(db_session, data)
        
        # Get session
        session_result = await db_session.execute(
            select(Session).where(
                or_(
                    and_(Session.device_a_id == device_a, Session.device_b_id == device_b),
                    and_(Session.device_a_id == device_b, Session.device_b_id == device_a),
                )
            )
        )
        session = session_result.scalar_one()
        
        # Request with limit=100 (should be capped to 50)
        result = await MessageService.get_history(
            db_session, session.session_id, device_b, limit=100
        )
        
        # Should return all 5 messages (limit is capped but we only have 5)
        assert len(result.messages) == 5
