"""Block schemas."""
from pydantic import BaseModel, Field


class BlockRequest(BaseModel):
    """Block user request."""
    device_id: str = Field(..., min_length=32, max_length=32)
    target_id: str = Field(..., min_length=32, max_length=32)
