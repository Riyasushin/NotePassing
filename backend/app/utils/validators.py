"""Validation utilities."""
from typing import List

from app.utils.uuid_utils import is_valid_device_id, is_valid_temp_id
from app.utils.exceptions import InvalidParamsError


def validate_device_id(device_id: str, field_name: str = "device_id") -> None:
    """
    Validate device ID format.
    
    Args:
        device_id: Device ID to validate
        field_name: Field name for error message
    
    Raises:
        InvalidParamsError: If device_id is invalid
    """
    if not device_id:
        raise InvalidParamsError(f"{field_name} is required")
    
    if not is_valid_device_id(device_id):
        raise InvalidParamsError(f"{field_name} must be a valid UUID v4 (32 character hex)")


def validate_temp_id(temp_id: str, field_name: str = "temp_id") -> None:
    """
    Validate temp ID format.
    
    Args:
        temp_id: Temp ID to validate
        field_name: Field name for error message
    
    Raises:
        InvalidParamsError: If temp_id is invalid
    """
    if not temp_id:
        raise InvalidParamsError(f"{field_name} is required")
    
    if not is_valid_temp_id(temp_id):
        raise InvalidParamsError(f"{field_name} must be a valid temp ID (32 character hex)")


def validate_nickname(nickname: str) -> None:
    """
    Validate nickname.
    
    Args:
        nickname: Nickname to validate
    
    Raises:
        InvalidParamsError: If nickname is invalid
    """
    if not nickname:
        raise InvalidParamsError("nickname is required")
    
    if len(nickname) > 50:
        raise InvalidParamsError("nickname must not exceed 50 characters")


def validate_profile(profile: str) -> None:
    """
    Validate profile text.
    
    Args:
        profile: Profile text to validate
    
    Raises:
        InvalidParamsError: If profile is invalid
    """
    if profile and len(profile) > 200:
        raise InvalidParamsError("profile must not exceed 200 characters")


def validate_tags(tags: List[str]) -> None:
    """
    Validate tags list.
    
    Args:
        tags: Tags list to validate
    
    Raises:
        InvalidParamsError: If tags is invalid
    """
    if tags is None:
        return
    
    if not isinstance(tags, list):
        raise InvalidParamsError("tags must be a list")
    
    for tag in tags:
        if not isinstance(tag, str):
            raise InvalidParamsError("all tags must be strings")


def validate_content(content: str, max_length: int = 1000, field_name: str = "content") -> None:
    """
    Validate message content.
    
    Args:
        content: Content to validate
        max_length: Maximum allowed length
        field_name: Field name for error message
    
    Raises:
        InvalidParamsError: If content is invalid
    """
    if not content:
        raise InvalidParamsError(f"{field_name} is required")
    
    if len(content) > max_length:
        raise InvalidParamsError(f"{field_name} must not exceed {max_length} characters")
