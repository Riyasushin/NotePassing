"""
临时ID Schema - Temp ID相关的Pydantic模型
"""

from pydantic import BaseModel, Field
from typing import Optional


class TempIdRefreshRequest(BaseModel):
    """临时ID刷新请求"""
    device_id: str = Field(..., description="设备ID")
    current_temp_id: Optional[str] = Field(None, description="当前使用的临时ID")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_id": "550e8400-e29b-41d4-a716-446655440001",
                "current_temp_id": "a1b2c3d4e5f6789012345678abcdef01"
            }
        }
    )


class TempIdRefreshResponse(BaseModel):
    """临时ID刷新响应"""
    temp_id: str = Field(..., description="新的临时ID (32字符十六进制)")
    expires_at: str = Field(..., description="过期时间 (ISO 8601)")
