"""Tests for temp ID service and endpoints."""
import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.temp_id_service import TempIDService
from app.services.device_service import DeviceService
from app.schemas.temp_id import TempIDRefreshRequest
from app.schemas.device import DeviceInitRequest
from app.utils.uuid_utils import generate_device_id, is_valid_temp_id
from app.utils.exceptions import DeviceNotInitializedError, InvalidParamsError
from app.config import get_settings

settings = get_settings()


class TestTempIDService:
    """Test TempIDService methods."""
    
    @pytest.mark.asyncio
    async def test_refresh_temp_id_new(self, db_session: AsyncSession):
        """Test generating a new temp ID."""
        device_id = generate_device_id()
        
        # Create device first
        await DeviceService.init_device(
            db_session,
            DeviceInitRequest(device_id=device_id, nickname="Test User")
        )
        
        data = TempIDRefreshRequest(device_id=device_id)
        result = await TempIDService.refresh_temp_id(db_session, data)
        
        assert is_valid_temp_id(result.temp_id)
        assert len(result.temp_id) == 32
        assert result.expires_at > datetime.utcnow()
        # Should expire in approximately 10 minutes
        assert result.expires_at > datetime.utcnow() + timedelta(minutes=9)
        assert result.expires_at < datetime.utcnow() + timedelta(minutes=11)
    
    @pytest.mark.asyncio
    async def test_refresh_temp_id_with_current(self, db_session: AsyncSession):
        """Test refreshing temp ID with a current one."""
        device_id = generate_device_id()
        
        # Create device
        await DeviceService.init_device(
            db_session,
            DeviceInitRequest(device_id=device_id, nickname="Test User")
        )
        
        # Get first temp ID
        data1 = TempIDRefreshRequest(device_id=device_id)
        result1 = await TempIDService.refresh_temp_id(db_session, data1)
        first_temp_id = result1.temp_id
        first_expires_at = result1.expires_at
        
        # Refresh with current temp ID
        data2 = TempIDRefreshRequest(
            device_id=device_id,
            current_temp_id=first_temp_id
        )
        result2 = await TempIDService.refresh_temp_id(db_session, data2)
        
        # New temp ID should be different
        assert result2.temp_id != first_temp_id
        assert is_valid_temp_id(result2.temp_id)
    
    @pytest.mark.asyncio
    async def test_refresh_temp_id_device_not_found(self, db_session: AsyncSession):
        """Test refreshing temp ID for non-existent device."""
        device_id = generate_device_id()
        
        data = TempIDRefreshRequest(device_id=device_id)
        
        with pytest.raises(DeviceNotInitializedError):
            await TempIDService.refresh_temp_id(db_session, data)
    
    @pytest.mark.asyncio
    async def test_refresh_temp_id_invalid_device_id(self, db_session: AsyncSession):
        """Test refreshing with invalid device ID."""
        from app.utils.validators import validate_device_id
        
        # Test validator directly (Pydantic schema already validates format)
        with pytest.raises(InvalidParamsError):
            validate_device_id("invalid-device-id")
    
    @pytest.mark.asyncio
    async def test_get_device_by_temp_id(self, db_session: AsyncSession):
        """Test looking up device by temp ID."""
        device_id = generate_device_id()
        
        # Create device
        await DeviceService.init_device(
            db_session,
            DeviceInitRequest(device_id=device_id, nickname="Test User")
        )
        
        # Generate temp ID
        data = TempIDRefreshRequest(device_id=device_id)
        result = await TempIDService.refresh_temp_id(db_session, data)
        
        # Look up device by temp ID
        found_device_id = await TempIDService.get_device_by_temp_id(
            db_session, result.temp_id
        )
        
        assert found_device_id == device_id
    
    @pytest.mark.asyncio
    async def test_get_device_by_temp_id_not_found(self, db_session: AsyncSession):
        """Test looking up non-existent temp ID."""
        found_device_id = await TempIDService.get_device_by_temp_id(
            db_session, "a" * 32
        )
        
        assert found_device_id is None
    
    @pytest.mark.asyncio
    async def test_get_device_by_temp_id_expired(self, db_session: AsyncSession):
        """Test looking up expired temp ID."""
        device_id = generate_device_id()
        
        # Create device
        await DeviceService.init_device(
            db_session,
            DeviceInitRequest(device_id=device_id, nickname="Test User")
        )
        
        # Generate temp ID
        data = TempIDRefreshRequest(device_id=device_id)
        result = await TempIDService.refresh_temp_id(db_session, data)
        
        # Manually expire the temp ID
        from app.models.temp_id import TempID
        from sqlalchemy import update
        
        await db_session.execute(
            update(TempID)
            .where(TempID.temp_id == result.temp_id)
            .values(expires_at=datetime.utcnow() - timedelta(minutes=1))
        )
        await db_session.commit()
        
        # Look up should return None (expired)
        found_device_id = await TempIDService.get_device_by_temp_id(
            db_session, result.temp_id
        )
        
        assert found_device_id is None
    
    @pytest.mark.asyncio
    async def test_validate_temp_id(self, db_session: AsyncSession):
        """Test validating temp ID."""
        device_id = generate_device_id()
        
        # Create device
        await DeviceService.init_device(
            db_session,
            DeviceInitRequest(device_id=device_id, nickname="Test User")
        )
        
        # Generate temp ID
        data = TempIDRefreshRequest(device_id=device_id)
        result = await TempIDService.refresh_temp_id(db_session, data)
        
        # Validate without ownership check
        is_valid = await TempIDService.validate_temp_id(
            db_session, result.temp_id
        )
        assert is_valid is True
        
        # Validate with correct ownership
        is_valid = await TempIDService.validate_temp_id(
            db_session, result.temp_id, device_id
        )
        assert is_valid is True
        
        # Validate with wrong ownership
        is_valid = await TempIDService.validate_temp_id(
            db_session, result.temp_id, "b" * 32
        )
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_validate_temp_id_invalid(self, db_session: AsyncSession):
        """Test validating invalid temp ID."""
        # Invalid format
        is_valid = await TempIDService.validate_temp_id(
            db_session, "invalid"
        )
        assert is_valid is False
        
        # Non-existent temp ID
        is_valid = await TempIDService.validate_temp_id(
            db_session, "a" * 32
        )
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_temp_ids(self, db_session: AsyncSession):
        """Test cleaning up expired temp IDs."""
        device_id = generate_device_id()
        
        # Create device
        await DeviceService.init_device(
            db_session,
            DeviceInitRequest(device_id=device_id, nickname="Test User")
        )
        
        # Generate temp ID
        data = TempIDRefreshRequest(device_id=device_id)
        result = await TempIDService.refresh_temp_id(db_session, data)
        
        # Manually expire the temp ID
        from app.models.temp_id import TempID
        from sqlalchemy import update
        
        await db_session.execute(
            update(TempID)
            .where(TempID.temp_id == result.temp_id)
            .values(expires_at=datetime.utcnow() - timedelta(minutes=1))
        )
        await db_session.commit()
        
        # Cleanup
        deleted_count = await TempIDService.cleanup_expired_temp_ids(db_session)
        
        assert deleted_count >= 1
        
        # Verify it's deleted
        found_device_id = await TempIDService.get_device_by_temp_id(
            db_session, result.temp_id
        )
        assert found_device_id is None


class TestTempIDEndpoints:
    """Test temp ID API endpoints."""
    
    @pytest.mark.asyncio
    async def test_refresh_temp_id_endpoint(self, client: AsyncClient):
        """Test POST /api/v1/temp-id/refresh."""
        device_id = generate_device_id()
        
        # Create device first
        await client.post("/api/v1/device/init", json={
            "device_id": device_id,
            "nickname": "Test User",
        })
        
        # Refresh temp ID
        response = await client.post("/api/v1/temp-id/refresh", json={
            "device_id": device_id,
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert is_valid_temp_id(data["data"]["temp_id"])
        assert "expires_at" in data["data"]
    
    @pytest.mark.asyncio
    async def test_refresh_temp_id_with_current_endpoint(self, client: AsyncClient):
        """Test refreshing with current_temp_id."""
        device_id = generate_device_id()
        
        # Create device
        await client.post("/api/v1/device/init", json={
            "device_id": device_id,
            "nickname": "Test User",
        })
        
        # Get first temp ID
        response1 = await client.post("/api/v1/temp-id/refresh", json={
            "device_id": device_id,
        })
        first_temp_id = response1.json()["data"]["temp_id"]
        
        # Refresh with current temp ID
        response2 = await client.post("/api/v1/temp-id/refresh", json={
            "device_id": device_id,
            "current_temp_id": first_temp_id,
        })
        
        assert response2.status_code == 200
        data = response2.json()
        assert data["code"] == 0
        assert data["data"]["temp_id"] != first_temp_id
    
    @pytest.mark.asyncio
    async def test_refresh_temp_id_device_not_found(self, client: AsyncClient):
        """Test refreshing for non-existent device."""
        device_id = generate_device_id()
        
        response = await client.post("/api/v1/temp-id/refresh", json={
            "device_id": device_id,
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 4007  # DEVICE_NOT_INITIALIZED
    
    @pytest.mark.asyncio
    async def test_refresh_temp_id_invalid_device_id(self, client: AsyncClient):
        """Test refreshing with invalid device ID."""
        response = await client.post("/api/v1/temp-id/refresh", json={
            "device_id": "invalid",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 5001  # INVALID_PARAMS
