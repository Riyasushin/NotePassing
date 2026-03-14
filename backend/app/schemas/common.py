"""Common response schemas."""
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar('T')


class ResponseModel(BaseModel, Generic[T]):
    """Standard API response wrapper."""
    code: int
    message: str
    data: Optional[T] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    code: int
    message: str
    data: None = None
