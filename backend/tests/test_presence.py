"""Tests for Phase 3: Presence Service - BLE nearby device resolution."""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import select

from app.models.presence import Presence
from app.models.device import Device
from app.models.temp_id import TempID
from app.models.friendship import Friendship
from app.models.session import Session
from app.models.block import Block
from app.schemas.presence import (
    PresenceResolveRequest,
    PresenceDisconnectRequest,
    ScannedDevice,
)
from app.services.presence_service import PresenceService
from app.services.device_service import DeviceService


@pytest.fixture
async def presence_devices(db_session):
    """Create two initialized devices for presence tests with unique IDs."""
    import uuid
    # Generate unique IDs to avoid conflicts
    id1 = uuid.uuid4().hex
    id2 = uuid.uuid4().hex
    
    device1 = Device(
        device_id=id1,
        nickname="Device One",
        tags=["tag1", "tag2"],
        is_anonymous=False,
    )
    device2 = Device(
        device_id=id2,
        nickname="Device Two",
        tags=["tag3", "tag4"],
        is_anonymous=True,
        role_name="Stranger",
    )
    db_session.add_all([device1, device2])
    await db_session.commit()
    return device1, device2


@pytest.fixture
async def presence_temp_ids(db_session, presence_devices):
    """Create temp IDs for both devices."""
    device1, device2 = presence_devices
    now = datetime.utcnow()
    
    temp_id1 = TempID(
        temp_id="t1" + device1.device_id[:30],
        device_id=device1.device_id,
        created_at=now,
        expires_at=now + timedelta(minutes=10),
    )
    temp_id2 = TempID(
        temp_id="t2" + device2.device_id[:30],
        device_id=device2.device_id,
        created_at=now,
        expires_at=now + timedelta(minutes=10),
    )
    db_session.add_all([temp_id1, temp_id2])
    await db_session.commit()
    return temp_id1, temp_id2


class TestResolveNearbyDevices:
    """Tests for resolving nearby devices."""
    
    async def test_resolve_single_device(self, db_session, presence_temp_ids):
        """Test resolving a single nearby device."""
        temp_id1, temp_id2 = presence_temp_ids
        
        request = PresenceResolveRequest(
            device_id=temp_id1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-65)
            ]
        )
        
        result = await PresenceService.resolve_nearby_devices(db_session, request)
        
        assert len(result.nearby_devices) == 1
        device = result.nearby_devices[0]
        assert device.temp_id == temp_id2.temp_id
        assert device.device_id == temp_id2.device_id
        assert device.nickname == "Device Two"
        assert device.is_anonymous is True
        assert device.role_name == "Stranger"
        # Distance should be estimated based on RSSI
        assert device.distance_estimate > 0
    
    async def test_resolve_multiple_devices(self, db_session, presence_temp_ids):
        """Test resolving multiple nearby devices."""
        temp_id1, temp_id2 = presence_temp_ids
        device1 = await db_session.get(Device, temp_id1.device_id)
        
        # Create third device with unique ID
        import uuid
        device3 = Device(
            device_id=uuid.uuid4().hex,
            nickname="Device Three",
            tags=["gaming"],
            is_anonymous=False,
        )
        db_session.add(device3)
        await db_session.commit()
        
        temp_id3 = TempID(
            temp_id="t3" + device3.device_id[:30],
            device_id=device3.device_id,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=10),
        )
        db_session.add(temp_id3)
        await db_session.commit()
        
        request = PresenceResolveRequest(
            device_id=device1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-65),
                ScannedDevice(temp_id=temp_id3.temp_id, rssi=-75),
            ]
        )
        
        result = await PresenceService.resolve_nearby_devices(db_session, request)
        
        assert len(result.nearby_devices) == 2
        device_ids = [d.device_id for d in result.nearby_devices]
        assert temp_id2.device_id in device_ids
        assert device3.device_id in device_ids
    
    async def test_resolve_skips_self(self, db_session, presence_temp_ids):
        """Test that self is skipped during resolution."""
        temp_id1, temp_id2 = presence_temp_ids
        
        request = PresenceResolveRequest(
            device_id=temp_id1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id=temp_id1.temp_id, rssi=-50),  # Self
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-65),
            ]
        )
        
        result = await PresenceService.resolve_nearby_devices(db_session, request)
        
        assert len(result.nearby_devices) == 1
        assert result.nearby_devices[0].device_id == temp_id2.device_id
    
    async def test_resolve_skips_blocked_devices(self, db_session, presence_temp_ids):
        """Test that blocked devices are filtered out."""
        temp_id1, temp_id2 = presence_temp_ids
        
        # Create block
        block = Block(
            device_id=temp_id1.device_id,
            target_id=temp_id2.device_id,
        )
        db_session.add(block)
        await db_session.commit()
        
        request = PresenceResolveRequest(
            device_id=temp_id1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-65),
            ]
        )
        
        result = await PresenceService.resolve_nearby_devices(db_session, request)
        
        assert len(result.nearby_devices) == 0
    
    async def test_resolve_skips_blocked_by_other(self, db_session, presence_temp_ids):
        """Test devices that have blocked you are filtered out."""
        temp_id1, temp_id2 = presence_temp_ids
        
        # Create block (other device blocked requester)
        block = Block(
            device_id=temp_id2.device_id,
            target_id=temp_id1.device_id,
        )
        db_session.add(block)
        await db_session.commit()
        
        request = PresenceResolveRequest(
            device_id=temp_id1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-65),
            ]
        )
        
        result = await PresenceService.resolve_nearby_devices(db_session, request)
        
        assert len(result.nearby_devices) == 0
    
    async def test_resolve_skips_invalid_temp_id(self, db_session, presence_temp_ids):
        """Test that invalid/expired temp IDs are skipped."""
        temp_id1, temp_id2 = presence_temp_ids
        
        request = PresenceResolveRequest(
            device_id=temp_id1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id="invalid" + "x" * 25, rssi=-65),
            ]
        )
        
        result = await PresenceService.resolve_nearby_devices(db_session, request)
        
        assert len(result.nearby_devices) == 0
    
    async def test_resolve_updates_presence_record(self, db_session, presence_temp_ids):
        """Test that presence record is created/updated."""
        temp_id1, temp_id2 = presence_temp_ids
        
        request = PresenceResolveRequest(
            device_id=temp_id1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-65),
            ]
        )
        
        await PresenceService.resolve_nearby_devices(db_session, request)
        
        # Check presence record
        result = await db_session.execute(
            select(Presence).where(
                Presence.device_id == temp_id1.device_id,
                Presence.nearby_device_id == temp_id2.device_id,
            )
        )
        presence = result.scalar_one()
        assert presence.rssi == -65
        assert presence.last_seen_at is not None
    
    async def test_resolve_presence_record_updated(self, db_session, presence_temp_ids):
        """Test that existing presence record is updated."""
        temp_id1, temp_id2 = presence_temp_ids
        
        # Create initial presence
        old_presence = Presence(
            device_id=temp_id1.device_id,
            nearby_device_id=temp_id2.device_id,
            rssi=-80,
            last_seen_at=datetime.utcnow() - timedelta(minutes=10),
        )
        db_session.add(old_presence)
        await db_session.commit()
        
        request = PresenceResolveRequest(
            device_id=temp_id1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-55),
            ]
        )
        
        await PresenceService.resolve_nearby_devices(db_session, request)
        
        # Verify updated
        await db_session.refresh(old_presence)
        assert old_presence.rssi == -55
        assert old_presence.last_seen_at > datetime.utcnow() - timedelta(minutes=1)
    
    async def test_resolve_uninitialized_device_raises(self, db_session, presence_temp_ids):
        """Test that uninitialized requester device raises error."""
        temp_id1, temp_id2 = presence_temp_ids
        
        import uuid
        request = PresenceResolveRequest(
            device_id=uuid.uuid4().hex,  # Not initialized
            scanned_devices=[
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-65),
            ]
        )
        
        from app.utils.exceptions import DeviceNotInitializedError
        with pytest.raises(DeviceNotInitializedError):
            await PresenceService.resolve_nearby_devices(db_session, request)
    
    async def test_resolve_identifies_friends(self, db_session, presence_temp_ids):
        """Test that friend status is correctly identified."""
        temp_id1, temp_id2 = presence_temp_ids
        import uuid
        
        # Create friendship with required request_id
        friendship = Friendship(
            request_id=str(uuid.uuid4()),
            sender_id=temp_id1.device_id,
            receiver_id=temp_id2.device_id,
            status="accepted",
        )
        db_session.add(friendship)
        await db_session.commit()
        
        request = PresenceResolveRequest(
            device_id=temp_id1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-65),
            ]
        )
        
        result = await PresenceService.resolve_nearby_devices(db_session, request)
        
        assert len(result.nearby_devices) == 1
        assert result.nearby_devices[0].is_friend is True
    
    async def test_resolve_identifies_strangers(self, db_session, presence_temp_ids):
        """Test that non-friends are identified as strangers."""
        temp_id1, temp_id2 = presence_temp_ids
        
        request = PresenceResolveRequest(
            device_id=temp_id1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-65),
            ]
        )
        
        result = await PresenceService.resolve_nearby_devices(db_session, request)
        
        assert len(result.nearby_devices) == 1
        assert result.nearby_devices[0].is_friend is False
    
    async def test_distance_estimation(self, db_session, presence_temp_ids):
        """Test distance estimation based on RSSI."""
        temp_id1, temp_id2 = presence_temp_ids
        
        request = PresenceResolveRequest(
            device_id=temp_id1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-40),  # Strong signal
            ]
        )
        
        result = await PresenceService.resolve_nearby_devices(db_session, request)
        
        assert len(result.nearby_devices) == 1
        # Strong signal = closer distance
        assert result.nearby_devices[0].distance_estimate < 2.0
    
    async def test_distance_estimation_far(self, db_session, presence_temp_ids):
        """Test distance estimation for weak signal."""
        temp_id1, temp_id2 = presence_temp_ids
        
        request = PresenceResolveRequest(
            device_id=temp_id1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-85),  # Weak signal
            ]
        )
        
        result = await PresenceService.resolve_nearby_devices(db_session, request)
        
        assert len(result.nearby_devices) == 1
        # Weak signal = farther distance
        assert result.nearby_devices[0].distance_estimate > 10.0


class TestBoostDetection:
    """Tests for boost alert detection."""
    
    async def test_boost_triggered_for_new_friend(self, db_session, presence_temp_ids):
        """Test boost is triggered when friend comes nearby for first time."""
        temp_id1, temp_id2 = presence_temp_ids
        import uuid
        
        # Create friendship with required request_id
        friendship = Friendship(
            request_id=str(uuid.uuid4()),
            sender_id=temp_id1.device_id,
            receiver_id=temp_id2.device_id,
            status="accepted",
        )
        db_session.add(friendship)
        await db_session.commit()
        
        request = PresenceResolveRequest(
            device_id=temp_id1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-65),
            ]
        )
        
        result = await PresenceService.resolve_nearby_devices(db_session, request)
        
        # Boost triggered for friend coming nearby (no presence record before)
        assert len(result.boost_alerts) == 1
        alert = result.boost_alerts[0]
        assert alert.device_id == temp_id2.device_id
        assert alert.nickname == "Device Two"
        assert alert.distance_estimate > 0
    
    async def test_boost_not_triggered_for_stranger(self, db_session, presence_temp_ids):
        """Test boost is not triggered for non-friends."""
        temp_id1, temp_id2 = presence_temp_ids
        
        request = PresenceResolveRequest(
            device_id=temp_id1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-65),
            ]
        )
        
        result = await PresenceService.resolve_nearby_devices(db_session, request)
        
        assert len(result.boost_alerts) == 0
    
    async def test_boost_cooldown_prevents_duplicate(self, db_session, presence_temp_ids):
        """Test boost is not triggered during cooldown period."""
        temp_id1, temp_id2 = presence_temp_ids
        import uuid
        
        # Create friendship with required request_id
        friendship = Friendship(
            request_id=str(uuid.uuid4()),
            sender_id=temp_id1.device_id,
            receiver_id=temp_id2.device_id,
            status="accepted",
        )
        db_session.add(friendship)
        
        # Create presence with recent boost
        presence = Presence(
            device_id=temp_id1.device_id,
            nearby_device_id=temp_id2.device_id,
            rssi=-65,
            last_seen_at=datetime.utcnow() - timedelta(minutes=10),
            last_boost_at=datetime.utcnow() - timedelta(minutes=2),  # Recent boost
        )
        db_session.add(presence)
        await db_session.commit()
        
        request = PresenceResolveRequest(
            device_id=temp_id1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-65),
            ]
        )
        
        result = await PresenceService.resolve_nearby_devices(db_session, request)
        
        # Should not trigger boost due to cooldown
        assert len(result.boost_alerts) == 0
    
    async def test_boost_after_cooldown_expires(self, db_session, presence_temp_ids):
        """Test boost is triggered after cooldown expires."""
        temp_id1, temp_id2 = presence_temp_ids
        import uuid
        
        # Create friendship with required request_id
        friendship = Friendship(
            request_id=str(uuid.uuid4()),
            sender_id=temp_id1.device_id,
            receiver_id=temp_id2.device_id,
            status="accepted",
        )
        db_session.add(friendship)
        
        # Create presence with old boost (cooldown expired)
        presence = Presence(
            device_id=temp_id1.device_id,
            nearby_device_id=temp_id2.device_id,
            rssi=-65,
            last_seen_at=datetime.utcnow() - timedelta(minutes=10),
            last_boost_at=datetime.utcnow() - timedelta(minutes=10),  # Old boost
        )
        db_session.add(presence)
        await db_session.commit()
        
        request = PresenceResolveRequest(
            device_id=temp_id1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-65),
            ]
        )
        
        result = await PresenceService.resolve_nearby_devices(db_session, request)
        
        # Should trigger boost after cooldown
        assert len(result.boost_alerts) == 1
    
    async def test_boost_not_triggered_if_already_nearby(self, db_session, presence_temp_ids):
        """Test boost is not triggered if friend was already nearby."""
        temp_id1, temp_id2 = presence_temp_ids
        import uuid
        
        # Create friendship with required request_id
        friendship = Friendship(
            request_id=str(uuid.uuid4()),
            sender_id=temp_id1.device_id,
            receiver_id=temp_id2.device_id,
            status="accepted",
        )
        db_session.add(friendship)
        
        # Create presence with recent last_seen (friend already nearby)
        presence = Presence(
            device_id=temp_id1.device_id,
            nearby_device_id=temp_id2.device_id,
            rssi=-65,
            last_seen_at=datetime.utcnow() - timedelta(minutes=2),  # Recently seen
            last_boost_at=datetime.utcnow() - timedelta(minutes=10),  # Old boost
        )
        db_session.add(presence)
        await db_session.commit()
        
        request = PresenceResolveRequest(
            device_id=temp_id1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-65),
            ]
        )
        
        result = await PresenceService.resolve_nearby_devices(db_session, request)
        
        # Should not trigger boost because friend was already nearby
        assert len(result.boost_alerts) == 0


class TestDisconnect:
    """Tests for disconnect reporting."""
    
    async def test_disconnect_removes_presence(self, db_session, presence_temp_ids):
        """Test that disconnect removes presence record."""
        temp_id1, temp_id2 = presence_temp_ids
        
        # Create presence record
        presence = Presence(
            device_id=temp_id1.device_id,
            nearby_device_id=temp_id2.device_id,
            rssi=-65,
            last_seen_at=datetime.utcnow(),
        )
        db_session.add(presence)
        await db_session.commit()
        
        request = PresenceDisconnectRequest(
            device_id=temp_id1.device_id,
            left_device_id=temp_id2.device_id,
        )
        
        await PresenceService.report_disconnect(db_session, request)
        await db_session.commit()
        
        # Verify presence removed
        result = await db_session.execute(
            select(Presence).where(
                Presence.device_id == temp_id1.device_id,
                Presence.nearby_device_id == temp_id2.device_id,
            )
        )
        assert result.scalar_one_or_none() is None
    
    async def test_disconnect_expires_temp_session(self, db_session, presence_temp_ids):
        """Test that disconnect expires temp session."""
        temp_id1, temp_id2 = presence_temp_ids
        
        # Determine device_a and device_b order (lexicographic)
        if temp_id1.device_id < temp_id2.device_id:
            device_a, device_b = temp_id1.device_id, temp_id2.device_id
        else:
            device_a, device_b = temp_id2.device_id, temp_id1.device_id
        
        # Create temp session
        session = Session(
            session_id="temp-session-123",
            device_a_id=device_a,
            device_b_id=device_b,
            is_temp=True,
            status="active",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=1),
        )
        db_session.add(session)
        await db_session.commit()
        
        request = PresenceDisconnectRequest(
            device_id=temp_id1.device_id,
            left_device_id=temp_id2.device_id,
        )
        
        result = await PresenceService.report_disconnect(db_session, request)
        await db_session.commit()
        
        assert result.session_expired is True
        assert result.session_id == "temp-session-123"
        
        # Verify session expired
        await db_session.refresh(session)
        assert session.status == "expired"
    
    async def test_disconnect_no_session(self, db_session, presence_temp_ids):
        """Test disconnect when no session exists."""
        temp_id1, temp_id2 = presence_temp_ids
        
        request = PresenceDisconnectRequest(
            device_id=temp_id1.device_id,
            left_device_id=temp_id2.device_id,
        )
        
        result = await PresenceService.report_disconnect(db_session, request)
        
        assert result.session_expired is False
        assert result.session_id is None
    
    async def test_disconnect_expires_only_temp_session(self, db_session, presence_temp_ids):
        """Test that disconnect only expires temp sessions, not permanent."""
        temp_id1, temp_id2 = presence_temp_ids
        
        # Determine device_a and device_b order (lexicographic)
        if temp_id1.device_id < temp_id2.device_id:
            device_a, device_b = temp_id1.device_id, temp_id2.device_id
        else:
            device_a, device_b = temp_id2.device_id, temp_id1.device_id
        
        # Create permanent session
        session = Session(
            session_id="perm-session-123",
            device_a_id=device_a,
            device_b_id=device_b,
            is_temp=False,
            status="active",
            created_at=datetime.utcnow(),
        )
        db_session.add(session)
        await db_session.commit()
        
        request = PresenceDisconnectRequest(
            device_id=temp_id1.device_id,
            left_device_id=temp_id2.device_id,
        )
        
        result = await PresenceService.report_disconnect(db_session, request)
        await db_session.commit()
        
        assert result.session_expired is False  # Permanent session not expired
        
        # Verify session still active
        await db_session.refresh(session)
        assert session.status == "active"


class TestPresencePrivacy:
    """Tests for privacy filtering in presence resolution."""
    
    async def test_stranger_sees_limited_info(self, db_session, presence_temp_ids):
        """Test that strangers see limited profile info."""
        temp_id1, temp_id2 = presence_temp_ids
        device2 = await db_session.get(Device, temp_id2.device_id)
        device2.is_anonymous = True
        await db_session.commit()
        
        request = PresenceResolveRequest(
            device_id=temp_id1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-65),
            ]
        )
        
        result = await PresenceService.resolve_nearby_devices(db_session, request)
        
        assert len(result.nearby_devices) == 1
        device = result.nearby_devices[0]
        # Anonymous device should show role_name instead of avatar
        assert device.role_name == "Stranger"
        assert device.is_anonymous is True
    
    async def test_friend_sees_full_info(self, db_session, presence_temp_ids):
        """Test that friends see full profile info."""
        temp_id1, temp_id2 = presence_temp_ids
        import uuid
        
        # Create friendship with required request_id
        friendship = Friendship(
            request_id=str(uuid.uuid4()),
            sender_id=temp_id1.device_id,
            receiver_id=temp_id2.device_id,
            status="accepted",
        )
        db_session.add(friendship)
        await db_session.commit()
        
        # Update device2 to have profile
        device2 = await db_session.get(Device, temp_id2.device_id)
        device2.profile = "Full profile info"
        device2.avatar = "avatar.png"
        await db_session.commit()
        
        request = PresenceResolveRequest(
            device_id=temp_id1.device_id,
            scanned_devices=[
                ScannedDevice(temp_id=temp_id2.temp_id, rssi=-65),
            ]
        )
        
        result = await PresenceService.resolve_nearby_devices(db_session, request)
        
        assert len(result.nearby_devices) == 1
        device = result.nearby_devices[0]
        assert device.is_friend is True
        assert device.profile == "Full profile info"


class TestPresenceEndpoints:
    """Tests for presence HTTP endpoints."""
    
    async def test_resolve_endpoint(self, client, db_session, presence_temp_ids):
        """Test POST /api/v1/presence/resolve endpoint."""
        temp_id1, temp_id2 = presence_temp_ids
        
        response = await client.post(
            "/api/v1/presence/resolve",
            json={
                "device_id": temp_id1.device_id,
                "scanned_devices": [
                    {"temp_id": temp_id2.temp_id, "rssi": -65}
                ]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0  # Success code
        assert len(data["data"]["nearby_devices"]) == 1
    
    async def test_disconnect_endpoint(self, client, db_session, presence_temp_ids):
        """Test POST /api/v1/presence/disconnect endpoint."""
        temp_id1, temp_id2 = presence_temp_ids
        
        response = await client.post(
            "/api/v1/presence/disconnect",
            json={
                "device_id": temp_id1.device_id,
                "left_device_id": temp_id2.device_id,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0  # Success code
        assert data["data"]["session_expired"] is False
    
    async def test_resolve_invalid_device_id(self, client):
        """Test resolve with invalid device ID format."""
        response = await client.post(
            "/api/v1/presence/resolve",
            json={
                "device_id": "invalid-id",
                "scanned_devices": []
            }
        )
        
        # API returns 200 with error code in body for validation errors
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 5001  # INVALID_PARAMS
        assert "device_id" in data["message"] or "32" in data["message"]
