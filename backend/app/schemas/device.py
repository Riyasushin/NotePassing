"""
设备Schema - 设备相关的Pydantic模型
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class DeviceInitRequest(BaseModel):
    """设备初始化请求"""
    device_id: str = Field(..., min_length=36, max_length=36, description="设备ID (UUID v4)")
    nickname: str = Field(..., min_length=1, max_length=50, description="昵称")
    tags: List[str] = Field(default=[], max_length=10, description="标签列表")
    profile: str = Field(default="", max_length=200, description="个人简介")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "device_id": "550e8400-e29b-41d4-a716-446655440001",
                "nickname": "小明",
                "tags": ["摄影", "旅行"],
                "profile": "喜欢拍照和旅行"
            }
        }
    )


class DeviceInitResponse(BaseModel):
    """设备初始化响应数据"""
    device_id: str
    nickname: str
    is_new: bool
    created_at: str


class DeviceUpdateRequest(BaseModel):
    """设备资料更新请求（部分更新）"""
    nickname: Optional[str] = Field(None, min_length=1, max_length=50)
    avatar: Optional[str] = Field(None, max_length=500)
    tags: Optional[List[str]] = Field(None, max_length=10)
    profile: Optional[str] = Field(None, max_length=200)
    is_anonymous: Optional[bool] = None
    role_name: Optional[str] = Field(None, max_length=50)
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "nickname": "新昵称",
                "is_anonymous": True,
                "role_name": "神秘人"
            }
        }
    )


class DeviceProfile(BaseModel):
    """设备资料（响应）"""
    device_id: str
    nickname: str
    avatar: Optional[str] = None
    tags: List[str] = []
    profile: str = ""
    is_anonymous: bool = False
    role_name: Optional[str] = None
    is_friend: bool = False
    
    model_config = ConfigDict(from_attributes=True)


class DeviceUpdateResponse(BaseModel):
    """设备更新响应数据"""
    device_id: str
    nickname: str
    avatar: Optional[str] = None
    tags: List[str] = []
    profile: str = ""
    is_anonymous: bool = False
    role_name: Optional[str] = None
    updated_at: str
