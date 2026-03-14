"""Device service for managing device operations."""
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.friendship import Friendship
from app.models.block import Block
from app.schemas.device import (
    DeviceInitRequest,
    DeviceInitResponse,
    DeviceUpdateRequest,
    DeviceProfileResponse,
)
from app.utils.validators import validate_device_id, validate_nickname, validate_profile, validate_tags
from app.utils.exceptions import DeviceNotInitializedError, InvalidParamsError, BlockedByUserError
from app.utils.uuid_utils import is_valid_device_id


class DeviceService:
    """Service for device operations."""
    
    @staticmethod
    async def init_device(db: AsyncSession, data: DeviceInitRequest) -> DeviceInitResponse:
        """
        Initialize or recover a device.
        
        Args:
            db: Database session
            data: Device initialization request
        
        Returns:
            Device initialization response
        """
        # Validate input
        validate_device_id(data.device_id)
        validate_nickname(data.nickname)
        if data.profile:
            validate_profile(data.profile)
        validate_tags(data.tags)
        
        # Check if device exists
        result = await db.execute(
            select(Device).where(Device.device_id == data.device_id)
        )
        device = result.scalar_one_or_none()
        
        if device:
            # Existing device - update nickname if changed
            is_new = False
            device.nickname = data.nickname
            if data.tags is not None:
                device.tags = data.tags
            if data.profile is not None:
                device.profile = data.profile
            device.updated_at = datetime.utcnow()
        else:
            # New device
            is_new = True
            device = Device(
                device_id=data.device_id,
                nickname=data.nickname,
                tags=data.tags or [],
                profile=data.profile,
            )
            db.add(device)
        
        await db.flush()
        
        return DeviceInitResponse(
            device_id=device.device_id,
            nickname=device.nickname,
            is_new=is_new,
            created_at=device.created_at,
        )
    
    @staticmethod
    async def get_device(
        db: AsyncSession,
        device_id: str,
        requester_id: str,
    ) -> DeviceProfileResponse:
        """
        Get device profile with privacy filtering.
        
        Args:
            db: Database session
            device_id: Target device ID
            requester_id: Requester device ID (for privacy filtering)
        
        Returns:
            Device profile response
        """
        # Validate inputs
        validate_device_id(device_id, "device_id")
        validate_device_id(requester_id, "requester_id")
        
        # Check if device exists
        result = await db.execute(
            select(Device).where(Device.device_id == device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            raise DeviceNotInitializedError()
        
        # Check if requester is blocked by target
        if device_id != requester_id:
            block_result = await db.execute(
                select(Block).where(
                    Block.device_id == device_id,
                    Block.target_id == requester_id,
                )
            )
            if block_result.scalar_one_or_none():
                raise BlockedByUserError()
        
        # Check friendship status
        is_friend = False
        if device_id != requester_id:
            friend_result = await db.execute(
                select(Friendship).where(
                    ((Friendship.sender_id == requester_id) & (Friendship.receiver_id == device_id))
                    | ((Friendship.sender_id == device_id) & (Friendship.receiver_id == requester_id))
                )
            )
            friendship = friend_result.scalar_one_or_none()
            is_friend = friendship is not None and friendship.status == "accepted"
        else:
            is_friend = True  # Self is always "friend"
        
        # Apply privacy rules
        avatar = device.avatar
        role_name = device.role_name
        
        # Stranger + anonymous mode: hide avatar, show role_name
        if not is_friend and device.is_anonymous:
            avatar = None
        
        # Stranger + not anonymous: show avatar, don't show role_name
        if not is_friend and not device.is_anonymous:
            role_name = None
        
        return DeviceProfileResponse(
            device_id=device.device_id,
            nickname=device.nickname,
            avatar=avatar,
            tags=device.tags or [],
            profile=device.profile,
            is_anonymous=device.is_anonymous,
            role_name=role_name,
            is_friend=is_friend,
        )
    
    @staticmethod
    async def update_device(
        db: AsyncSession,
        device_id: str,
        data: DeviceUpdateRequest,
    ) -> dict:
        """
        Update device profile (partial update).
        
        Args:
            db: Database session
            device_id: Device ID to update
            data: Update data (partial)
        
        Returns:
            Updated device data
        """
        # Validate device_id
        validate_device_id(device_id)
        
        # Get device
        result = await db.execute(
            select(Device).where(Device.device_id == device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            raise DeviceNotInitializedError()
        
        # Validate and apply updates
        if data.nickname is not None:
            validate_nickname(data.nickname)
            device.nickname = data.nickname
        
        if data.avatar is not None:
            device.avatar = data.avatar
        
        if data.tags is not None:
            validate_tags(data.tags)
            device.tags = data.tags
        
        if data.profile is not None:
            validate_profile(data.profile)
            device.profile = data.profile
        
        if data.is_anonymous is not None:
            device.is_anonymous = data.is_anonymous
        
        if data.role_name is not None:
            device.role_name = data.role_name
        
        device.updated_at = datetime.utcnow()
        await db.flush()
        
        return {
            "device_id": device.device_id,
            "nickname": device.nickname,
            "avatar": device.avatar,
            "tags": device.tags or [],
            "profile": device.profile,
            "is_anonymous": device.is_anonymous,
            "role_name": device.role_name,
            "updated_at": device.updated_at,
        }
    
    @staticmethod
    async def check_device_exists(db: AsyncSession, device_id: str) -> bool:
        """
        Check if a device exists.
        
        Args:
            db: Database session
            device_id: Device ID to check
        
        Returns:
            True if device exists
        """
        if not is_valid_device_id(device_id):
            return False
        
        result = await db.execute(
            select(Device.device_id).where(Device.device_id == device_id)
        )
        return result.scalar_one_or_none() is not None
