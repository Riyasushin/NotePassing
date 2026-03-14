"""Presence service for managing nearby device relationships."""
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.presence import Presence
from app.models.device import Device
from app.models.block import Block
from app.models.session import Session
from app.schemas.presence import (
    PresenceResolveRequest,
    PresenceResolveResponse,
    NearbyDevice,
    BoostAlert,
    PresenceDisconnectRequest,
    PresenceDisconnectResponse,
)
from app.services.temp_id_service import TempIDService
from app.services.device_service import DeviceService
from app.utils.validators import validate_device_id
from app.utils.exceptions import DeviceNotInitializedError
from app.utils.distance import estimate_distance
from app.config import get_settings

settings = get_settings()


class PresenceService:
    """Service for presence operations."""
    
    @staticmethod
    async def resolve_nearby_devices(
        db: AsyncSession,
        data: PresenceResolveRequest,
    ) -> PresenceResolveResponse:
        """
        Resolve scanned temp IDs to device profiles.
        
        Args:
            db: Database session
            data: Resolve request with scanned devices
        
        Returns:
            Resolved nearby devices and boost alerts
        """
        validate_device_id(data.device_id)
        
        # Check if requester device exists
        device_result = await db.execute(
            select(Device).where(Device.device_id == data.device_id)
        )
        if not device_result.scalar_one_or_none():
            raise DeviceNotInitializedError()
        
        nearby_devices: List[NearbyDevice] = []
        boost_alerts: List[BoostAlert] = []
        
        for scanned in data.scanned_devices:
            # Resolve temp_id to device_id
            target_device_id = await TempIDService.get_device_by_temp_id(
                db, scanned.temp_id
            )
            
            if not target_device_id:
                continue
            
            # Skip self
            if target_device_id == data.device_id:
                continue
            
            # Check if blocked (either direction)
            block_result = await db.execute(
                select(Block).where(
                    or_(
                        and_(
                            Block.device_id == data.device_id,
                            Block.target_id == target_device_id,
                        ),
                        and_(
                            Block.device_id == target_device_id,
                            Block.target_id == data.device_id,
                        ),
                    )
                )
            )
            if block_result.scalar_one_or_none():
                continue
            
            try:
                profile = await DeviceService.get_device(
                    db, target_device_id, data.device_id
                )
            except Exception:
                continue

            distance = estimate_distance(scanned.rssi)
            is_friend = profile.is_friend

            nearby_device = NearbyDevice(
                temp_id=scanned.temp_id,
                device_id=profile.device_id,
                nickname=profile.nickname,
                avatar=profile.avatar,
                tags=profile.tags,
                profile=profile.profile,
                is_anonymous=profile.is_anonymous,
                role_name=profile.role_name,
                distance_estimate=distance,
                is_friend=is_friend,
            )
            nearby_devices.append(nearby_device)

            boost_triggered = False
            if is_friend:
                boost = await PresenceService._check_boost(
                    db, data.device_id, target_device_id, distance
                )
                if boost:
                    boost_alerts.append(boost)
                    boost_triggered = True

            await PresenceService._update_presence(
                db, data.device_id, target_device_id, scanned.rssi,
                boost_triggered=boost_triggered,
            )
        
        return PresenceResolveResponse(
            nearby_devices=nearby_devices,
            boost_alerts=boost_alerts,
        )
    
    @staticmethod
    async def report_disconnect(
        db: AsyncSession,
        data: PresenceDisconnectRequest,
    ) -> PresenceDisconnectResponse:
        """
        Report a device leaving Bluetooth range.
        
        Args:
            db: Database session
            data: Disconnect report
        
        Returns:
            Disconnect response with session info
        """
        validate_device_id(data.device_id)
        validate_device_id(data.left_device_id, "left_device_id")
        
        # Update presence record
        await db.execute(
            delete(Presence).where(
                Presence.device_id == data.device_id,
                Presence.nearby_device_id == data.left_device_id,
            )
        )
        
        # Check for temp session to expire
        session_expired = False
        expired_session_id: Optional[str] = None
        
        # Find session between the two devices
        if data.device_id < data.left_device_id:
            device_a, device_b = data.device_id, data.left_device_id
        else:
            device_a, device_b = data.left_device_id, data.device_id
        
        session_result = await db.execute(
            select(Session).where(
                Session.device_a_id == device_a,
                Session.device_b_id == device_b,
                Session.is_temp == True,
                Session.status == "active",
            )
        )
        session = session_result.scalar_one_or_none()
        
        if session:
            session.status = "expired"
            session.expires_at = datetime.utcnow()
            session_expired = True
            expired_session_id = session.session_id
            await db.flush()
        
        return PresenceDisconnectResponse(
            session_expired=session_expired,
            session_id=expired_session_id,
        )
    
    @staticmethod
    async def _update_presence(
        db: AsyncSession,
        device_id: str,
        nearby_device_id: str,
        rssi: int,
        boost_triggered: bool = False,
    ) -> None:
        """Update or create presence record."""
        # Check if record exists
        result = await db.execute(
            select(Presence).where(
                Presence.device_id == device_id,
                Presence.nearby_device_id == nearby_device_id,
            )
        )
        presence = result.scalar_one_or_none()
        
        now = datetime.utcnow()
        
        if presence:
            # Update existing
            presence.rssi = rssi
            presence.last_seen_at = now
            if boost_triggered:
                presence.last_boost_at = now
        else:
            # Create new
            presence = Presence(
                device_id=device_id,
                nearby_device_id=nearby_device_id,
                rssi=rssi,
                last_seen_at=now,
                last_boost_at=now if boost_triggered else None,
            )
            db.add(presence)
        
        await db.flush()
    
    @staticmethod
    async def _check_boost(
        db: AsyncSession,
        device_id: str,
        friend_device_id: str,
        distance: float,
    ) -> Optional[BoostAlert]:
        """
        Check if boost should be triggered for friend coming nearby.
        
        Boost conditions:
        - Friend was not nearby recently (no presence record or last_seen_at > 5 min ago)
        - Last boost was more than 5 minutes ago
        """
        # Get presence record
        result = await db.execute(
            select(Presence).where(
                Presence.device_id == device_id,
                Presence.nearby_device_id == friend_device_id,
            )
        )
        presence = result.scalar_one_or_none()
        
        now = datetime.utcnow()
        cooldown = timedelta(minutes=settings.boost_cooldown_minutes)
        
        # Check last boost time
        if presence and presence.last_boost_at:
            time_since_boost = now - presence.last_boost_at
            if time_since_boost < cooldown:
                return None  # Still in cooldown
        
        # Check if friend was away (not seen in last 5 minutes)
        was_away = True
        if presence and presence.last_seen_at:
            time_since_seen = now - presence.last_seen_at
            if time_since_seen < timedelta(minutes=5):
                was_away = False  # Friend was already nearby
        
        if not was_away:
            return None
        
        # Get friend profile
        friend_result = await db.execute(
            select(Device).where(Device.device_id == friend_device_id)
        )
        friend = friend_result.scalar_one()
        
        return BoostAlert(
            device_id=friend_device_id,
            nickname=friend.nickname,
            distance_estimate=distance,
        )
