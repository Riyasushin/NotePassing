"""Custom exceptions for NotePassing API."""
from fastapi import HTTPException, status

from app.utils.error_codes import (
    TEMP_CHAT_LIMIT_REACHED,
    TEMP_SESSION_EXPIRED,
    NOT_IN_BLUETOOTH_RANGE,
    BLOCKED_BY_USER,
    FRIEND_REQUEST_COOLDOWN,
    INVALID_TEMP_ID,
    DEVICE_NOT_INITIALIZED,
    FRIENDSHIP_NOT_EXIST,
    DUPLICATE_OPERATION,
    INVALID_PARAMS,
    SERVER_ERROR,
    get_error_message,
)


class NotePassingException(Exception):
    """Base exception for business logic errors."""
    
    def __init__(self, code: int, message: str = None):
        self.code = code
        self.message = message or get_error_message(code)
        super().__init__(self.message)


class TempChatLimitReachedError(NotePassingException):
    """Non-friend sent more than 2 messages without reply."""
    def __init__(self):
        super().__init__(TEMP_CHAT_LIMIT_REACHED)


class TempSessionExpiredError(NotePassingException):
    """Temporary session expired after Bluetooth disconnected."""
    def __init__(self):
        super().__init__(TEMP_SESSION_EXPIRED)


class NotInBluetoothRangeError(NotePassingException):
    """Attempting to chat with non-nearby user."""
    def __init__(self):
        super().__init__(NOT_IN_BLUETOOTH_RANGE)


class BlockedByUserError(NotePassingException):
    """Blocked by the target user."""
    def __init__(self):
        super().__init__(BLOCKED_BY_USER)


class FriendRequestCooldownError(NotePassingException):
    """Friend request rejected within 24h."""
    def __init__(self):
        super().__init__(FRIEND_REQUEST_COOLDOWN)


class InvalidTempIDError(NotePassingException):
    """Temp ID expired or does not exist."""
    def __init__(self):
        super().__init__(INVALID_TEMP_ID)


class DeviceNotInitializedError(NotePassingException):
    """Device not initialized before using other APIs."""
    def __init__(self):
        super().__init__(DEVICE_NOT_INITIALIZED)


class FriendshipNotExistError(NotePassingException):
    """Operating on non-existent friendship."""
    def __init__(self):
        super().__init__(FRIENDSHIP_NOT_EXIST)


class DuplicateOperationError(NotePassingException):
    """Duplicate operation like sending friend request."""
    def __init__(self):
        super().__init__(DUPLICATE_OPERATION)


class InvalidParamsError(NotePassingException):
    """Invalid parameter format or missing required fields."""
    def __init__(self, message: str = None):
        super().__init__(INVALID_PARAMS, message)


class ServerError(NotePassingException):
    """Unexpected server error."""
    def __init__(self, message: str = None):
        super().__init__(SERVER_ERROR, message)


def setup_exception_handlers(app):
    """Setup exception handlers for FastAPI app."""
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from fastapi.exceptions import RequestValidationError
    from app.utils.response import error_response
    
    @app.exception_handler(NotePassingException)
    async def notepassing_exception_handler(request: Request, exc: NotePassingException):
        return JSONResponse(
            status_code=status.HTTP_200_OK,  # Always return 200 with code in body
            content=error_response(exc.code, exc.message)
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle Pydantic validation errors."""
        # Extract error message
        errors = exc.errors()
        if errors:
            msg = errors[0].get("msg", "参数格式错误")
            loc = errors[0].get("loc", [])
            message = f"{loc[-1] if loc else 'field'}: {msg}" if loc else msg
        else:
            message = "参数格式错误"
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=error_response(INVALID_PARAMS, message)
        )
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        if exc.status_code == 422:
            # Validation error
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content=error_response(INVALID_PARAMS, str(exc.detail))
            )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(SERVER_ERROR, str(exc.detail))
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(SERVER_ERROR, "服务器内部错误")
        )
