"""
通用Schema - 基础响应模型和通用类型
"""

from typing import Optional, TypeVar, Generic
from pydantic import BaseModel, ConfigDict


T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """
    统一响应格式
    
    所有API响应都使用此格式:
    {
        "code": 0,          # 错误码，0表示成功
        "message": "ok",    # 错误信息
        "data": {...}       # 响应数据
    }
    """
    model_config = ConfigDict(from_attributes=True)
    
    code: int = 0
    message: str = "ok"
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    """错误响应"""
    code: int
    message: str
    data: Optional[dict] = None


class PaginationParams(BaseModel):
    """分页参数"""
    before: Optional[str] = None  # 分页游标
    limit: int = 20  # 每页条数，默认20
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "before": "2026-03-14T10:53:00Z",
                "limit": 20
            }
        }
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应"""
    items: list[T]
    has_more: bool = False
    next_cursor: Optional[str] = None
