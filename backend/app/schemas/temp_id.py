"""Temp ID schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TempIDRefreshRequest(BaseModel):
    """Temp ID refresh request."""
    device_id: str = Field(..., min_length=32, max_length=32)
    current_temp_id: Optional[str] = Field(default=None, min_length=32, max_length=32)


class TempIDRefreshResponse(BaseModel):
    """Temp ID refresh response."""
    temp_id: str = Field(..., description="32 character hex string for BLE broadcast")
    expires_at: datetime
