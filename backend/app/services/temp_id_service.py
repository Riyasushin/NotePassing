"""Temp ID service for managing temporary BLE broadcast IDs."""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.temp_id import TempID
from app.models.device import Device
from app.schemas.temp_id import TempIDRefreshRequest, TempIDRefreshResponse
from app.utils.validators import validate_device_id, validate_temp_id
from app.utils.exceptions import (
    DeviceNotInitializedError,
    InvalidTempIDError,
    InvalidParamsError,
)
from app.utils.uuid_utils import generate_temp_id
from app.config import get_settings

settings = get_settings()


class TempIDService:
    """Service for temporary ID operations."""
    
    @staticmethod
    async def refresh_temp_id(
        db: AsyncSession,
        data: TempIDRefreshRequest,
    ) -> TempIDRefreshResponse:
        """
        Generate a new temp ID for BLE broadcast.
        If current_temp_id is provided, its expiration time will be shortened.
        
        Args:
            db: Database session
            data: Refresh request with device_id and optional current_temp_id
        
        Returns:
            New temp ID with expiration time
        """
        # Validate device_id
        validate_device_id(data.device_id)
        
        # Check if device exists
        result = await db.execute(
            select(Device).where(Device.device_id == data.device_id)
        )
        device = result.scalar_one_or_none()
        
        if not device:
            raise DeviceNotInitializedError()
        
        # If current_temp_id is provided, shorten its expiration
        if data.current_temp_id:
            validate_temp_id(data.current_temp_id)
            await TempIDService._shorten_temp_id_expiration(
                db, data.current_temp_id, data.device_id
            )
        
        # Generate new temp_id
        new_temp_id = generate_temp_id(data.device_id, settings.secret_key)
        
        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(
            minutes=settings.temp_id_expire_minutes
        )
        
        # Create new temp ID record
        temp_id_record = TempID(
            temp_id=new_temp_id,
            device_id=data.device_id,
            expires_at=expires_at,
        )
        db.add(temp_id_record)
        await db.flush()
        
        return TempIDRefreshResponse(
            temp_id=new_temp_id,
            expires_at=expires_at,
        )
    
    @staticmethod
    async def _shorten_temp_id_expiration(
        db: AsyncSession,
        temp_id: str,
        device_id: str,
    ) -> None:
        """
        Shorten the expiration time of an existing temp ID.
        Sets expiration to now + buffer_minutes.
        
        Args:
            db: Database session
            temp_id: The temp ID to shorten
            device_id: The device ID (for verification)
        """
        new_expires_at = datetime.utcnow() + timedelta(
            minutes=settings.temp_id_buffer_minutes
        )
        
        result = await db.execute(
            update(TempID)
            .where(
                TempID.temp_id == temp_id,
                TempID.device_id == device_id,
            )
            .values(expires_at=new_expires_at)
        )
        
        # If no rows were updated, the temp_id doesn't exist or belongs to another device
        # We don't raise an error here as it's not critical
    
    @staticmethod
    async def get_device_by_temp_id(
        db: AsyncSession,
        temp_id: str,
    ) -> Optional[str]:
        """
        Get device ID by temp ID.
        
        Args:
            db: Database session
            temp_id: The temp ID to look up
        
        Returns:
            Device ID if found and not expired, None otherwise
        """
        if not temp_id or len(temp_id) != 32:
            return None
        
        result = await db.execute(
            select(TempID).where(TempID.temp_id == temp_id)
        )
        temp_id_record = result.scalar_one_or_none()
        
        if not temp_id_record:
            return None
        
        if temp_id_record.is_expired():
            return None
        
        return temp_id_record.device_id
    
    @staticmethod
    async def validate_temp_id(
        db: AsyncSession,
        temp_id: str,
        device_id: Optional[str] = None,
    ) -> bool:
        """
        Validate if a temp ID is valid and optionally check ownership.
        
        Args:
            db: Database session
            temp_id: The temp ID to validate
            device_id: Optional device ID to check ownership
        
        Returns:
            True if valid, False otherwise
        """
        if not temp_id or len(temp_id) != 32:
            return False
        
        result = await db.execute(
            select(TempID).where(TempID.temp_id == temp_id)
        )
        temp_id_record = result.scalar_one_or_none()
        
        if not temp_id_record:
            return False
        
        if temp_id_record.is_expired():
            return False
        
        if device_id and temp_id_record.device_id != device_id:
            return False
        
        return True
    
    @staticmethod
    async def cleanup_expired_temp_ids(db: AsyncSession) -> int:
        """
        Clean up expired temp IDs from database.
        
        Args:
            db: Database session
        
        Returns:
            Number of deleted records
        """
        from sqlalchemy import delete
        
        result = await db.execute(
            delete(TempID).where(TempID.expires_at < datetime.utcnow())
        )
        
        return result.rowcount
