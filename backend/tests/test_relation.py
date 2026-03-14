"""Tests for relation service and endpoints."""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_

from app.services.relation_service import RelationService
from app.services.device_service import DeviceService
from app.schemas.friendship import (
    FriendRequestRequest,
    FriendResponseRequest,
)
from app.schemas.block import BlockRequest
from app.schemas.device import DeviceInitRequest
from app.utils.uuid_utils import generate_device_id, generate_uuid
from app.utils.exceptions import (
    DeviceNotInitializedError,
    BlockedByUserError,
    FriendRequestCooldownError,
    DuplicateOperationError,
    FriendshipNotExistError,
)
from app.models.friendship import Friendship
from app.models.block import Block
from app.models.session import Session


class TestRelationService:
    """Test RelationService methods."""
    
    @pytest.mark.asyncio
    async def test_get_friends(self, db_session: AsyncSession):
        """Test getting friend list."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        device_c = generate_device_id()
        
        # Create devices
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="User B")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_c, nickname="User C")
        )
        
        # Create friendships
        for friend_id in [device_b, device_c]:
            friendship = Friendship(
                request_id=generate_uuid(),
                sender_id=device_a,
                receiver_id=friend_id,
                status="accepted",
            )
            db_session.add(friendship)
        await db_session.commit()
        
        # Get friends
        result = await RelationService.get_friends(db_session, device_a)
        
        assert len(result.friends) == 2
        friend_ids = [f.device_id for f in result.friends]
        assert device_b in friend_ids
        assert device_c in friend_ids
    
    @pytest.mark.asyncio
    async def test_send_friend_request(self, db_session: AsyncSession):
        """Test sending friend request."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="User B")
        )
        
        # Send friend request
        data = FriendRequestRequest(
            sender_id=device_a,
            receiver_id=device_b,
            message="Let's be friends!",
        )
        result = await RelationService.send_friend_request(db_session, data)
        
        assert result.request_id is not None
        assert result.status == "pending"
        assert result.created_at is not None
    
    @pytest.mark.asyncio
    async def test_send_friend_request_blocked(self, db_session: AsyncSession):
        """Test sending friend request when blocked."""
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
        
        # A tries to send friend request to B
        data = FriendRequestRequest(
            sender_id=device_a,
            receiver_id=device_b,
        )
        with pytest.raises(BlockedByUserError):
            await RelationService.send_friend_request(db_session, data)
    
    @pytest.mark.asyncio
    async def test_send_friend_request_duplicate(self, db_session: AsyncSession):
        """Test sending duplicate friend request."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="User B")
        )
        
        # Send first request
        data = FriendRequestRequest(
            sender_id=device_a,
            receiver_id=device_b,
        )
        await RelationService.send_friend_request(db_session, data)
        
        # Try to send another request
        with pytest.raises(DuplicateOperationError):
            await RelationService.send_friend_request(db_session, data)
    
    @pytest.mark.asyncio
    async def test_send_friend_request_cooldown(self, db_session: AsyncSession):
        """Test friend request cooldown after rejection."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="User B")
        )
        
        # Create rejected friendship
        friendship = Friendship(
            request_id=generate_uuid(),
            sender_id=device_a,
            receiver_id=device_b,
            status="rejected",
            rejected_at=datetime.utcnow(),  # Just rejected
        )
        db_session.add(friendship)
        await db_session.commit()
        
        # Try to send request again (within 24h)
        data = FriendRequestRequest(
            sender_id=device_a,
            receiver_id=device_b,
        )
        with pytest.raises(FriendRequestCooldownError):
            await RelationService.send_friend_request(db_session, data)
        
        # After cooldown should work
        friendship.rejected_at = datetime.utcnow() - timedelta(hours=25)
        await db_session.commit()
        
        result = await RelationService.send_friend_request(db_session, data)
        assert result.status == "pending"
    
    @pytest.mark.asyncio
    async def test_accept_friend_request(self, db_session: AsyncSession):
        """Test accepting friend request."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="User B")
        )
        
        # Send friend request
        request_data = FriendRequestRequest(
            sender_id=device_a,
            receiver_id=device_b,
        )
        request_result = await RelationService.send_friend_request(db_session, request_data)
        
        # Accept request
        response_data = FriendResponseRequest(
            device_id=device_b,
            action="accept",
        )
        result = await RelationService.respond_friend_request(
            db_session, request_result.request_id, response_data
        )
        
        assert result.status == "accepted"
        assert result.friend is not None
        assert result.friend.device_id == device_a
        assert result.session_id is not None
        
        # Verify session is permanent
        session_result = await db_session.execute(
            select(Session).where(Session.session_id == result.session_id)
        )
        session = session_result.scalar_one()
        assert session.is_temp is False
    
    @pytest.mark.asyncio
    async def test_reject_friend_request(self, db_session: AsyncSession):
        """Test rejecting friend request."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="User B")
        )
        
        # Send friend request
        request_data = FriendRequestRequest(
            sender_id=device_a,
            receiver_id=device_b,
        )
        request_result = await RelationService.send_friend_request(db_session, request_data)
        
        # Reject request
        response_data = FriendResponseRequest(
            device_id=device_b,
            action="reject",
        )
        result = await RelationService.respond_friend_request(
            db_session, request_result.request_id, response_data
        )
        
        assert result.status == "rejected"
        assert result.friend is None
        assert result.session_id is None
    
    @pytest.mark.asyncio
    async def test_delete_friend(self, db_session: AsyncSession):
        """Test deleting friendship."""
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
        
        # Delete friendship
        await RelationService.delete_friend(db_session, device_a, device_b)
        
        # Verify deleted - check specifically for this pair
        result = await db_session.execute(
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
        assert result.scalar_one_or_none() is None
    
    @pytest.mark.asyncio
    async def test_block_user(self, db_session: AsyncSession):
        """Test blocking user."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="User B")
        )
        
        # Create friendship first
        friendship = Friendship(
            request_id=generate_uuid(),
            sender_id=device_a,
            receiver_id=device_b,
            status="accepted",
        )
        db_session.add(friendship)
        await db_session.commit()
        
        # Block user
        data = BlockRequest(
            device_id=device_a,
            target_id=device_b,
        )
        await RelationService.block_user(db_session, data)
        
        # Verify block created
        block_result = await db_session.execute(
            select(Block).where(
                Block.device_id == device_a,
                Block.target_id == device_b,
            )
        )
        assert block_result.scalar_one_or_none() is not None
        
        # Verify friendship deleted - check specifically for this pair
        friendship_result = await db_session.execute(
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
        assert friendship_result.scalar_one_or_none() is None
    
    @pytest.mark.asyncio
    async def test_unblock_user(self, db_session: AsyncSession):
        """Test unblocking user."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create devices
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        await DeviceService.init_device(
            db_session, DeviceInitRequest(device_id=device_b, nickname="User B")
        )
        
        # Create block
        block = Block(device_id=device_a, target_id=device_b)
        db_session.add(block)
        await db_session.commit()
        
        # Unblock
        await RelationService.unblock_user(db_session, device_a, device_b)
        
        # Verify block removed
        block_result = await db_session.execute(
            select(Block).where(
                Block.device_id == device_a,
                Block.target_id == device_b,
            )
        )
        assert block_result.scalar_one_or_none() is None


class TestRelationEndpoints:
    """Test relation API endpoints."""
    
    @pytest.mark.asyncio
    async def test_get_friends_endpoint(self, client: AsyncClient):
        """Test GET /api/v1/friends."""
        device_a = generate_device_id()
        
        # Create device
        await client.post("/api/v1/device/init", json={
            "device_id": device_a,
            "nickname": "User A",
        })
        
        # Test endpoint returns successfully
        response = await client.get(f"/api/v1/friends?device_id={device_a}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert "friends" in data["data"]
    
    @pytest.mark.asyncio
    async def test_send_friend_request_endpoint(self, client: AsyncClient):
        """Test POST /api/v1/friends/request."""
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
        
        # Send friend request
        response = await client.post("/api/v1/friends/request", json={
            "sender_id": device_a,
            "receiver_id": device_b,
            "message": "Let's be friends!",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["status"] == "pending"
    
    @pytest.mark.asyncio
    async def test_block_user_endpoint(self, client: AsyncClient):
        """Test POST /api/v1/block."""
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
        
        # Block user
        response = await client.post("/api/v1/block", json={
            "device_id": device_a,
            "target_id": device_b,
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
