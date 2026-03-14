"""UUID and ID generation utilities."""
import uuid
import hashlib
import secrets
from datetime import datetime


def generate_device_id() -> str:
    """
    Generate a new device ID (UUID v4).
    
    Returns:
        UUID v4 string (32 character hex without dashes)
    """
    return uuid.uuid4().hex


def generate_uuid() -> str:
    """
    Generate a standard UUID.
    
    Returns:
        UUID string with dashes
    """
    return str(uuid.uuid4())


def generate_temp_id(device_id: str, secret_key: str) -> str:
    """
    Generate a temporary ID for BLE broadcast.
    
    Generation rule: hex(hash(device_id + secret_key + timestamp + random_salt))
    
    Args:
        device_id: The device ID
        secret_key: Server secret key
    
    Returns:
        32 character hexadecimal string
    """
    timestamp = str(int(datetime.utcnow().timestamp()))
    random_salt = secrets.token_hex(8)
    
    data = f"{device_id}{secret_key}{timestamp}{random_salt}"
    hash_obj = hashlib.sha256(data.encode())
    
    return hash_obj.hexdigest()[:32]


def is_valid_uuid(val: str) -> bool:
    """
    Check if a string is a valid UUID.
    
    Args:
        val: String to check
    
    Returns:
        True if valid UUID, False otherwise
    """
    try:
        uuid.UUID(val)
        return True
    except (ValueError, TypeError):
        return False


def is_valid_device_id(device_id: str) -> bool:
    """
    Check if a string is a valid device ID (UUID v4 format, no dashes).
    
    Args:
        device_id: Device ID string
    
    Returns:
        True if valid, False otherwise
    """
    if not device_id or not isinstance(device_id, str):
        return False
    
    # Device ID should be 32 character hex string
    if len(device_id) != 32:
        return False
    
    try:
        int(device_id, 16)
        return True
    except ValueError:
        return False


def is_valid_temp_id(temp_id: str) -> bool:
    """
    Check if a string is a valid temp ID (32 character hex).
    
    Args:
        temp_id: Temp ID string
    
    Returns:
        True if valid, False otherwise
    """
    if not temp_id or not isinstance(temp_id, str):
        return False
    
    if len(temp_id) != 32:
        return False
    
    try:
        int(temp_id, 16)
        return True
    except ValueError:
        return False
