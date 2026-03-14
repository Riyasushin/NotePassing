"""Response utilities for NotePassing API."""
from typing import Any, Optional

from app.utils.error_codes import SUCCESS, get_error_message


def success_response(data: Any = None, message: str = "ok") -> dict:
    """
    Create a standard success response.
    
    Args:
        data: Response data
        message: Success message
    
    Returns:
        Standardized response dict
    """
    return {
        "code": SUCCESS,
        "message": message,
        "data": data
    }


def error_response(code: int, message: Optional[str] = None) -> dict:
    """
    Create a standard error response.
    
    Args:
        code: Error code
        message: Error message (optional, uses default if not provided)
    
    Returns:
        Standardized error response dict
    """
    return {
        "code": code,
        "message": message or get_error_message(code),
        "data": None
    }
