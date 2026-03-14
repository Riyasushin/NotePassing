"""Integration tests for complete business flows."""
import pytest
import asyncio
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.services.device_service import DeviceService
from app.services.temp_id_service import TempIDService
from app.services.message_service import MessageService
from app.services.relation_service import RelationService
from app.schemas.device import DeviceInitRequest, DeviceUpdateRequest
from app.schemas.temp_id import TempIDRefreshRequest
from app.schemas.message import SendMessageRequest, MarkReadRequest
from app.schemas.friendship import FriendRequestRequest, FriendResponseRequest
from app.schemas.block import BlockRequest
from app.utils.uuid_utils import generate_device_id
from app.models.device import Device
from app.models.friendship import Friendship
from app.models.block import Block
from app.models.session import Session
from app.models.message import Message
from app.models.temp_id import TempID


class TestCompleteBusinessFlow:
    """Test complete business scenarios."""
    
    @pytest.mark.asyncio
    async def test_two_users_meet_and_chat(self, db_session: AsyncSession):
        """
        Complete flow: Two users meet, chat as strangers, become friends.
        
        Scenario:
        1. Device A and B initialize
        2. B gets temp_id (BLE broadcast)
        3. A scans B's temp_id
        4. A gets B's profile
        5. A sends message to B (creates temp session)
        6. B replies (temp session continues)
        7. A sends friend request
        8. B accepts
        9. They become friends with permanent session
        10. Exchange more messages as friends
        """
        # Step 1: Initialize devices
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        await DeviceService.init_device(
            db_session,
            DeviceInitRequest(device_id=device_a, nickname="Alice", tags=["coffee"])
        )
        await DeviceService.init_device(
            db_session,
            DeviceInitRequest(device_id=device_b, nickname="Bob", tags=["music"])
        )
        
        # Step 2: B gets temp_id (simulates BLE broadcast)
        temp_id_result = await TempIDService.refresh_temp_id(
            db_session,
            TempIDRefreshRequest(device_id=device_b)
        )
        b_temp_id = temp_id_result.temp_id
        
        # Step 3: A scans B's temp_id and resolves
        b_device_id = await TempIDService.get_device_by_temp_id(db_session, b_temp_id)
        assert b_device_id == device_b
        
        # Step 4: A gets B's profile
        b_profile = await DeviceService.get_device(db_session, device_b, device_a)
        assert b_profile.nickname == "Bob"
        assert b_profile.is_friend is False
        
        # Step 5: A sends message to B (temp session)
        msg1 = await MessageService.send_message(
            db_session,
            SendMessageRequest(
                sender_id=device_a,
                receiver_id=device_b,
                content="Hey, I like your taste in music!",
                type="common",
            )
        )
        assert msg1.session_id is not None
        
        # Verify temp session created
        session_result = await db_session.execute(
            select(Session).where(Session.session_id == msg1.session_id)
        )
        session = session_result.scalar_one()
        assert session.is_temp is True
        
        # Step 6: B replies
        msg2 = await MessageService.send_message(
            db_session,
            SendMessageRequest(
                sender_id=device_b,
                receiver_id=device_a,
                content="Thanks! I see you like coffee too!",
                type="common",
            )
        )
        
        # Step 7: A sends friend request
        friend_req = await RelationService.send_friend_request(
            db_session,
            FriendRequestRequest(
                sender_id=device_a,
                receiver_id=device_b,
                message="Want to be friends?",
            )
        )
        assert friend_req.status == "pending"
        
        # Step 8: B accepts
        friend_resp = await RelationService.respond_friend_request(
            db_session,
            friend_req.request_id,
            FriendResponseRequest(device_id=device_b, action="accept")
        )
        assert friend_resp.status == "accepted"
        assert friend_resp.session_id is not None
        
        # Step 9: Verify permanent session
        perm_session_result = await db_session.execute(
            select(Session).where(Session.session_id == friend_resp.session_id)
        )
        perm_session = perm_session_result.scalar_one()
        assert perm_session.is_temp is False
        
        # Step 10: Exchange messages as friends (no limits)
        for i in range(5):
            await MessageService.send_message(
                db_session,
                SendMessageRequest(
                    sender_id=device_a,
                    receiver_id=device_b,
                    content=f"Friend message {i+1}",
                    type="common",
                )
            )
        
        # Verify all messages sent
        history = await MessageService.get_history(
            db_session, perm_session.session_id, device_b, limit=20
        )
        assert len(history.messages) >= 7  # 2 temp + 5 friend messages
    
    @pytest.mark.asyncio
    async def test_user_blocks_another(self, db_session: AsyncSession):
        """
        Test blocking flow:
        1. A and B are friends
        2. A blocks B
        3. Friendship is removed
        4. B cannot message A
        5. B cannot send friend request
        """
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Setup: Initialize and be friends
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="Alice")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="Bob")
        )
        
        # Create friendship
        friend_req = await RelationService.send_friend_request(
            db_session,
            FriendRequestRequest(sender_id=device_a, receiver_id=device_b)
        )
        await RelationService.respond_friend_request(
            db_session,
            friend_req.request_id,
            FriendResponseRequest(device_id=device_b, action="accept")
        )
        
        # Verify they can message
        await MessageService.send_message(
            db_session,
            SendMessageRequest(
                sender_id=device_b,
                receiver_id=device_a,
                content="Hello friend!",
            )
        )
        
        # Step 2: A blocks B
        await RelationService.block_user(
            db_session,
            BlockRequest(device_id=device_a, target_id=device_b)
        )
        
        # Step 3: Verify friendship removed
        friends = await RelationService.get_friends(db_session, device_a)
        assert len(friends.friends) == 0
        
        # Step 4: B cannot message A
        from app.utils.exceptions import BlockedByUserError
        with pytest.raises(BlockedByUserError):
            await MessageService.send_message(
                db_session,
                SendMessageRequest(
                    sender_id=device_b,
                    receiver_id=device_a,
                    content="Can you hear me?",
                )
            )
        
        # Step 5: B cannot send friend request
        with pytest.raises(BlockedByUserError):
            await RelationService.send_friend_request(
                db_session,
                FriendRequestRequest(sender_id=device_b, receiver_id=device_a)
            )
    
    @pytest.mark.asyncio
    async def test_temp_session_expires_after_disconnect(self, db_session: AsyncSession):
        """
        Test temp session expiration:
        1. A and B chat as strangers (temp session)
        2. B leaves Bluetooth range
        3. A reports disconnect
        4. Temp session expires
        5. A cannot send more messages
        """
        from app.utils.exceptions import TempSessionExpiredError
        
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Setup
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="Alice")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="Bob")
        )
        
        # Create temp session via message
        msg = await MessageService.send_message(
            db_session,
            SendMessageRequest(
                sender_id=device_a,
                receiver_id=device_b,
                content="Hello stranger!",
            )
        )
        
        # Get the session
        session_result = await db_session.execute(
            select(Session).where(Session.session_id == msg.session_id)
        )
        session = session_result.scalar_one()
        
        # Expire the session manually (simulating time passing)
        session.expires_at = datetime.utcnow() - timedelta(minutes=1)
        await db_session.commit()
        
        # Try to send message - should fail
        with pytest.raises(TempSessionExpiredError):
            await MessageService.send_message(
                db_session,
                SendMessageRequest(
                    sender_id=device_a,
                    receiver_id=device_b,
                    content="Are you still there?",
                )
            )


class TestErrorScenarios:
    """Test error handling scenarios."""
    
    @pytest.mark.asyncio
    async def test_duplicate_friend_request(self, db_session: AsyncSession):
        """Test sending duplicate friend request."""
        from app.utils.exceptions import DuplicateOperationError
        
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="Alice")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="Bob")
        )
        
        # First request
        await RelationService.send_friend_request(
            db_session,
            FriendRequestRequest(sender_id=device_a, receiver_id=device_b)
        )
        
        # Duplicate should fail
        with pytest.raises(DuplicateOperationError):
            await RelationService.send_friend_request(
                db_session,
                FriendRequestRequest(sender_id=device_a, receiver_id=device_b)
            )
    
    @pytest.mark.asyncio
    async def test_message_to_nonexistent_device(self, db_session: AsyncSession):
        """Test messaging a non-existent device."""
        from app.utils.exceptions import DeviceNotInitializedError
        
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="Alice")
        )
        
        with pytest.raises(DeviceNotInitializedError):
            await MessageService.send_message(
                db_session,
                SendMessageRequest(
                    sender_id=device_a,
                    receiver_id=device_b,
                    content="Hello?",
                )
            )
    
    @pytest.mark.asyncio
    async def test_temp_chat_limit(self, db_session: AsyncSession):
        """Test temp session 2-message limit."""
        from app.utils.exceptions import TempChatLimitReachedError
        
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="Alice")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="Bob")
        )
        
        # Send 2 messages
        for i in range(2):
            await MessageService.send_message(
                db_session,
                SendMessageRequest(
                    sender_id=device_a,
                    receiver_id=device_b,
                    content=f"Message {i+1}",
                )
            )
        
        # 3rd message should fail
        with pytest.raises(TempChatLimitReachedError):
            await MessageService.send_message(
                db_session,
                SendMessageRequest(
                    sender_id=device_a,
                    receiver_id=device_b,
                    content="Message 3 - should fail",
                )
            )


class TestPrivacyAndSecurity:
    """Test privacy and security features."""
    
    @pytest.mark.asyncio
    async def test_anonymous_mode_hides_avatar(self, db_session: AsyncSession):
        """Test that anonymous mode hides avatar from strangers."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Setup: B is anonymous
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="Alice")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="Bob")
        )
        await DeviceService.update_device(
            db_session,
            device_b,
            DeviceUpdateRequest(
                avatar="https://example.com/avatar.jpg",
                is_anonymous=True,
                role_name="Mystery Person"
            )
        )
        
        # A views B's profile
        profile = await DeviceService.get_device(db_session, device_b, device_a)
        
        # Should not see avatar
        assert profile.avatar is None
        # Should see role_name
        assert profile.role_name == "Mystery Person"
    
    @pytest.mark.asyncio
    async def test_friends_can_see_full_profile(self, db_session: AsyncSession):
        """Test that friends can see full profile including avatar."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Setup
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="Alice")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="Bob")
        )
        await DeviceService.update_device(
            db_session,
            device_b,
            DeviceUpdateRequest(
                avatar="https://example.com/avatar.jpg",
                is_anonymous=True,
            )
        )
        
        # Become friends
        friend_req = await RelationService.send_friend_request(
            db_session,
            FriendRequestRequest(sender_id=device_a, receiver_id=device_b)
        )
        await RelationService.respond_friend_request(
            db_session,
            friend_req.request_id,
            FriendResponseRequest(device_id=device_b, action="accept")
        )
        
        # A views B's profile as friend
        profile = await DeviceService.get_device(db_session, device_b, device_a)
        
        # Should see avatar
        assert profile.avatar == "https://example.com/avatar.jpg"
        # Should be marked as friend
        assert profile.is_friend is True


class TestAPIIntegration:
    """Integration tests using HTTP client."""
    
    @pytest.mark.asyncio
    async def test_full_api_flow(self, client: AsyncClient):
        """Test complete flow via API endpoints."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Step 1: Initialize devices
        resp_a = await client.post("/api/v1/device/init", json={
            "device_id": device_a,
            "nickname": "Alice",
            "tags": ["coffee"],
        })
        assert resp_a.status_code == 200
        assert resp_a.json()["code"] == 0
        
        resp_b = await client.post("/api/v1/device/init", json={
            "device_id": device_b,
            "nickname": "Bob",
            "tags": ["music"],
        })
        assert resp_b.status_code == 200
        
        # Step 2: B gets temp_id
        resp_temp = await client.post("/api/v1/temp-id/refresh", json={
            "device_id": device_b,
        })
        assert resp_temp.status_code == 200
        b_temp_id = resp_temp.json()["data"]["temp_id"]
        
        # Step 3: A gets B's profile
        resp_profile = await client.get(f"/api/v1/device/{device_b}?requester_id={device_a}")
        assert resp_profile.status_code == 200
        assert resp_profile.json()["data"]["nickname"] == "Bob"
        
        # Step 4: A sends message to B
        resp_msg = await client.post("/api/v1/messages", json={
            "sender_id": device_a,
            "receiver_id": device_b,
            "content": "Hello via API!",
            "type": "common",
        })
        assert resp_msg.status_code == 200
        session_id = resp_msg.json()["data"]["session_id"]
        
        # Step 5: Get message history
        resp_history = await client.get(
            f"/api/v1/messages/{session_id}?device_id={device_b}&limit=10"
        )
        assert resp_history.status_code == 200
        assert len(resp_history.json()["data"]["messages"]) == 1
        
        # Step 6: Send friend request
        resp_req = await client.post("/api/v1/friends/request", json={
            "sender_id": device_a,
            "receiver_id": device_b,
            "message": "Let's be friends!",
        })
        assert resp_req.status_code == 200
        request_id = resp_req.json()["data"]["request_id"]
        
        # Step 7: B accepts
        resp_accept = await client.put(f"/api/v1/friends/{request_id}", json={
            "device_id": device_b,
            "action": "accept",
        })
        assert resp_accept.status_code == 200
        assert resp_accept.json()["data"]["status"] == "accepted"
        
        # Step 8: Get friends list
        resp_friends = await client.get(f"/api/v1/friends?device_id={device_a}")
        assert resp_friends.status_code == 200
        friends = resp_friends.json()["data"]["friends"]
        assert len(friends) == 1
        assert friends[0]["device_id"] == device_b
