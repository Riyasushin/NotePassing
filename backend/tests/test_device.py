"""Tests for device service and endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.device_service import DeviceService
from app.schemas.device import DeviceInitRequest, DeviceUpdateRequest
from app.utils.uuid_utils import generate_device_id


class TestDeviceService:
    """Test DeviceService methods."""
    
    @pytest.mark.asyncio
    async def test_init_device_new(self, db_session: AsyncSession):
        """Test initializing a new device."""
        device_id = generate_device_id()
        data = DeviceInitRequest(
            device_id=device_id,
            nickname="Test User",
            tags=["test", "demo"],
            profile="Test profile",
        )
        
        result = await DeviceService.init_device(db_session, data)
        
        assert result.device_id == device_id
        assert result.nickname == "Test User"
        assert result.is_new is True
        assert result.created_at is not None
    
    @pytest.mark.asyncio
    async def test_init_device_existing(self, db_session: AsyncSession):
        """Test recovering an existing device."""
        device_id = generate_device_id()
        
        # First init
        data1 = DeviceInitRequest(
            device_id=device_id,
            nickname="Original Name",
            tags=["original"],
        )
        await DeviceService.init_device(db_session, data1)
        
        # Second init (should recover)
        data2 = DeviceInitRequest(
            device_id=device_id,
            nickname="Updated Name",
            tags=["updated"],
        )
        result = await DeviceService.init_device(db_session, data2)
        
        assert result.is_new is False
        assert result.nickname == "Updated Name"
    
    @pytest.mark.asyncio
    async def test_init_device_invalid_id(self, db_session: AsyncSession):
        """Test init with invalid device ID."""
        from app.utils.exceptions import InvalidParamsError
        
        # Test through service directly with invalid ID
        with pytest.raises(InvalidParamsError):
            # Use 32 chars but invalid hex
            data = DeviceInitRequest(
                device_id="gggggggggggggggggggggggggggggggg",  # Invalid hex
                nickname="Test",
            )
            await DeviceService.init_device(db_session, data)
    
    @pytest.mark.asyncio
    async def test_init_device_nickname_too_long(self, db_session: AsyncSession):
        """Test init with nickname exceeding limit."""
        from app.utils.exceptions import InvalidParamsError
        from app.utils.validators import validate_nickname
        
        # Test validator directly
        with pytest.raises(InvalidParamsError):
            validate_nickname("x" * 51)  # Exceeds 50 char limit
    
    @pytest.mark.asyncio
    async def test_get_device_self(self, db_session: AsyncSession):
        """Test getting own device profile."""
        device_id = generate_device_id()
        
        # Create device
        init_data = DeviceInitRequest(
            device_id=device_id,
            nickname="Self User",
            tags=["self"],
            profile="My profile",
        )
        await DeviceService.init_device(db_session, init_data)
        
        # Get own profile
        result = await DeviceService.get_device(db_session, device_id, device_id)
        
        assert result.device_id == device_id
        assert result.nickname == "Self User"
        assert result.is_friend is True
        assert result.tags == ["self"]
    
    @pytest.mark.asyncio
    async def test_get_device_stranger_anonymous(self, db_session: AsyncSession):
        """Test getting stranger profile when target is anonymous."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create device A (requester)
        await DeviceService.init_device(
            db_session,
            DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        
        # Create device B (target, anonymous)
        await DeviceService.init_device(
            db_session,
            DeviceInitRequest(device_id=device_b, nickname="User B")
        )
        await DeviceService.update_device(
            db_session,
            device_b,
            DeviceUpdateRequest(is_anonymous=True, role_name="Mystery Person")
        )
        
        # Get B's profile from A
        result = await DeviceService.get_device(db_session, device_b, device_a)
        
        assert result.device_id == device_b
        assert result.is_anonymous is True
        assert result.nickname == "不愿透露姓名的ta"
        assert result.avatar is None  # Hidden for anonymous strangers
        assert result.tags == []
        assert result.profile == ""
        assert result.role_name is None
        assert result.is_friend is False
    
    @pytest.mark.asyncio
    async def test_get_device_stranger_not_anonymous(self, db_session: AsyncSession):
        """Test getting stranger profile when target is not anonymous."""
        device_a = generate_device_id()
        device_b = generate_device_id()
        
        # Create both devices
        await DeviceService.init_device(
            db_session,
            DeviceInitRequest(device_id=device_a, nickname="User A")
        )
        await DeviceService.init_device(
            db_session,
            DeviceInitRequest(device_id=device_b, nickname="User B")
        )
        await DeviceService.update_device(
            db_session,
            device_b,
            DeviceUpdateRequest(avatar="https://example.com/avatar.jpg")
        )
        
        # Get B's profile from A
        result = await DeviceService.get_device(db_session, device_b, device_a)
        
        assert result.avatar == "https://example.com/avatar.jpg"
        assert result.role_name is None  # Not shown for non-anonymous
        assert result.is_friend is False
    
    @pytest.mark.asyncio
    async def test_get_device_not_found(self, db_session: AsyncSession):
        """Test getting non-existent device."""
        requester_id = generate_device_id()
        
        # Create requester
        await DeviceService.init_device(
            db_session,
            DeviceInitRequest(device_id=requester_id, nickname="Requester")
        )
        
        from app.utils.exceptions import DeviceNotInitializedError
        with pytest.raises(DeviceNotInitializedError):
            await DeviceService.get_device(db_session, generate_device_id(), requester_id)
    
    @pytest.mark.asyncio
    async def test_update_device(self, db_session: AsyncSession):
        """Test updating device profile."""
        device_id = generate_device_id()
        
        # Create device
        await DeviceService.init_device(
            db_session,
            DeviceInitRequest(device_id=device_id, nickname="Original")
        )
        
        # Update
        update_data = DeviceUpdateRequest(
            nickname="Updated",
            avatar="https://new-avatar.jpg",
            tags=["new", "tags"],
            is_anonymous=True,
        )
        result = await DeviceService.update_device(db_session, device_id, update_data)
        
        assert result["nickname"] == "Updated"
        assert result["avatar"] == "https://new-avatar.jpg"
        assert result["tags"] == ["new", "tags"]
        assert result["is_anonymous"] is True
        assert result["updated_at"] is not None
    
    @pytest.mark.asyncio
    async def test_update_device_partial(self, db_session: AsyncSession):
        """Test partial update (only some fields)."""
        device_id = generate_device_id()
        
        # Create device with avatar
        await DeviceService.init_device(
            db_session,
            DeviceInitRequest(device_id=device_id, nickname="User")
        )
        await DeviceService.update_device(
            db_session,
            device_id,
            DeviceUpdateRequest(avatar="https://original.jpg")
        )
        
        # Update only nickname
        result = await DeviceService.update_device(
            db_session,
            device_id,
            DeviceUpdateRequest(nickname="New Name")
        )
        
        assert result["nickname"] == "New Name"
        assert result["avatar"] == "https://original.jpg"  # Unchanged
    
    @pytest.mark.asyncio
    async def test_update_device_not_found(self, db_session: AsyncSession):
        """Test updating non-existent device."""
        from app.utils.exceptions import DeviceNotInitializedError
        
        with pytest.raises(DeviceNotInitializedError):
            await DeviceService.update_device(
                db_session,
                generate_device_id(),
                DeviceUpdateRequest(nickname="New")
            )
    
    @pytest.mark.asyncio
    async def test_check_device_exists(self, db_session: AsyncSession):
        """Test checking device existence."""
        device_id = generate_device_id()
        
        # Should not exist
        assert await DeviceService.check_device_exists(db_session, device_id) is False
        
        # Create device
        await DeviceService.init_device(
            db_session,
            DeviceInitRequest(device_id=device_id, nickname="User")
        )
        
        # Should exist
        assert await DeviceService.check_device_exists(db_session, device_id) is True
    
    @pytest.mark.asyncio
    async def test_check_device_exists_invalid_id(self, db_session: AsyncSession):
        """Test checking with invalid device ID."""
        assert await DeviceService.check_device_exists(db_session, "invalid") is False


class TestDeviceEndpoints:
    """Test device API endpoints."""
    
    @pytest.mark.asyncio
    async def test_init_device_endpoint_new(self, client: AsyncClient):
        """Test POST /api/v1/device/init for new device."""
        device_id = generate_device_id()
        
        response = await client.post("/api/v1/device/init", json={
            "device_id": device_id,
            "nickname": "New User",
            "tags": ["new"],
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["is_new"] is True
        assert data["data"]["nickname"] == "New User"
    
    @pytest.mark.asyncio
    async def test_init_device_endpoint_existing(self, client: AsyncClient):
        """Test POST /api/v1/device/init for existing device."""
        device_id = generate_device_id()
        
        # First init
        await client.post("/api/v1/device/init", json={
            "device_id": device_id,
            "nickname": "First",
        })
        
        # Second init
        response = await client.post("/api/v1/device/init", json={
            "device_id": device_id,
            "nickname": "Second",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["is_new"] is False
    
    @pytest.mark.asyncio
    async def test_init_device_endpoint_validation_error(self, client: AsyncClient):
        """Test init endpoint with invalid data."""
        response = await client.post("/api/v1/device/init", json={
            "device_id": "invalid",
            "nickname": "Valid Nick",
        })
        
        # Should return 200 with error code in body (handled by exception handler)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 5001  # INVALID_PARAMS
    
    @pytest.mark.asyncio
    async def test_get_device_endpoint(self, client: AsyncClient):
        """Test GET /api/v1/device/{device_id}."""
        device_id = generate_device_id()
        
        # Create device
        await client.post("/api/v1/device/init", json={
            "device_id": device_id,
            "nickname": "Target User",
        })
        
        # Get device
        response = await client.get(f"/api/v1/device/{device_id}?requester_id={device_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["device_id"] == device_id
        assert data["data"]["nickname"] == "Target User"
    
    @pytest.mark.asyncio
    async def test_get_device_endpoint_not_found(self, client: AsyncClient):
        """Test GET device endpoint for non-existent device."""
        requester_id = generate_device_id()
        
        # Create requester
        await client.post("/api/v1/device/init", json={
            "device_id": requester_id,
            "nickname": "Requester",
        })
        
        # Try to get non-existent device
        response = await client.get(f"/api/v1/device/{generate_device_id()}?requester_id={requester_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 4007  # DEVICE_NOT_INITIALIZED
    
    @pytest.mark.asyncio
    async def test_update_device_endpoint(self, client: AsyncClient):
        """Test PUT /api/v1/device/{device_id}."""
        device_id = generate_device_id()
        
        # Create device
        await client.post("/api/v1/device/init", json={
            "device_id": device_id,
            "nickname": "Original",
        })
        
        # Update
        response = await client.put(f"/api/v1/device/{device_id}", json={
            "nickname": "Updated",
            "avatar": "https://new.jpg",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["nickname"] == "Updated"
        assert data["data"]["avatar"] == "https://new.jpg"
    
    @pytest.mark.asyncio
    async def test_update_device_endpoint_not_found(self, client: AsyncClient):
        """Test PUT device endpoint for non-existent device."""
        response = await client.put(f"/api/v1/device/{generate_device_id()}", json={
            "nickname": "Updated",
        })
        
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 4007  # DEVICE_NOT_INITIALIZED

    @pytest.mark.asyncio
    async def test_upload_avatar_endpoint(self, client: AsyncClient):
        """Test POST /api/v1/device/{device_id}/avatar."""
        device_id = generate_device_id()

        await client.post("/api/v1/device/init", json={
            "device_id": device_id,
            "nickname": "Avatar User",
        })

        response = await client.post(
            f"/api/v1/device/{device_id}/avatar",
            files={"file": ("avatar.jpg", b"fake-image-bytes", "image/jpeg")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["avatar_url"].startswith("http://test/uploads/avatars/")

        avatar_path = data["data"]["avatar_url"].removeprefix("http://test")
        avatar_response = await client.get(avatar_path)
        assert avatar_response.status_code == 200
        assert avatar_response.content == b"fake-image-bytes"

        profile_response = await client.get(f"/api/v1/device/{device_id}?requester_id={device_id}")
        profile_data = profile_response.json()
        assert profile_data["data"]["avatar"] == data["data"]["avatar_url"]

    @pytest.mark.asyncio
    async def test_upload_avatar_endpoint_rejects_non_image(self, client: AsyncClient):
        """Test avatar upload rejects non-image files."""
        device_id = generate_device_id()

        await client.post("/api/v1/device/init", json={
            "device_id": device_id,
            "nickname": "Avatar User",
        })

        response = await client.post(
            f"/api/v1/device/{device_id}/avatar",
            files={"file": ("avatar.txt", b"plain-text", "text/plain")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 5001
    
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
