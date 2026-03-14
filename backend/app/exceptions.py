"""Custom exceptions and error handlers."""

from fastapi import HTTPException
from fastapi.responses import JSONResponse


class NotePassingException(Exception):
    """Base exception for NotePassing server."""
    
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class ValidationError(NotePassingException):
    """Validation error (5001)."""
    def __init__(self, message: str = "参数格式错误"):
        super().__init__(5001, message)


class DeviceNotInitializedError(NotePassingException):
    """Device not initialized error (4007)."""
    def __init__(self):
        super().__init__(4007, "设备未初始化")


class FriendshipNotFoundError(NotePassingException):
    """Friendship not found error (4008)."""
    def __init__(self):
        super().__init__(4008, "好友关系不存在")


class DuplicateOperationError(NotePassingException):
    """Duplicate operation error (4009)."""
    def __init__(self):
        super().__init__(4009, "重复操作")


class BlockedError(NotePassingException):
    """Blocked by user error (4004)."""
    def __init__(self):
        super().__init__(4004, "已被对方屏蔽")


class CooldownError(NotePassingException):
    """Cooldown error (4005)."""
    def __init__(self):
        super().__init__(4005, "好友申请冷却中")


class TempMessageLimitError(NotePassingException):
    """Temp message limit error (4001)."""
    def __init__(self):
        super().__init__(4001, "临时聊天消息已达上限")


# Error code mapping
ERROR_CODES = {
    0: "成功",
    4001: "临时聊天消息已达上限",
    4002: "临时会话已过期",
    4003: "不在蓝牙范围内",
    4004: "已被对方屏蔽",
    4005: "好友申请冷却中",
    4006: "无效的临时 ID",
    4007: "设备未初始化",
    4008: "好友关系不存在",
    4009: "重复操作",
    5001: "参数格式错误",
    5002: "服务器内部错误",
}


def create_error_response(code: int, message: str = None) -> JSONResponse:
    """Create standardized error response."""
    if message is None:
        message = ERROR_CODES.get(code, "未知错误")
    
    return JSONResponse(
        status_code=200,  # Always return 200 with error code in body
        content={
            "code": code,
            "message": message,
            "data": None,
        },
    )


def create_success_response(data: dict = None) -> dict:
    """Create standardized success response."""
    return {
        "code": 0,
        "message": "ok",
        "data": data,
    }
