"""
验证工具 - 输入验证函数
"""

import re
import uuid
from typing import Tuple


def is_valid_uuid(uuid_str: str) -> bool:
    """
    验证字符串是否为有效的UUID v4
    
    Args:
        uuid_str: 要验证的字符串
        
    Returns:
        bool: 是否为有效的UUID
    """
    if not uuid_str:
        return False
    
    # UUID v4 格式: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
    # 其中 y 是 8, 9, a, 或 b
    pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    
    if not re.match(pattern, uuid_str.lower()):
        return False
    
    try:
        uuid.UUID(uuid_str)
        return True
    except ValueError:
        return False


def validate_nickname(nickname: str) -> Tuple[bool, str]:
    """
    验证昵称
    
    Returns:
        (是否有效, 错误信息)
    """
    if not nickname:
        return False, "昵称不能为空"
    
    if len(nickname) > 50:
        return False, "昵称长度不能超过50字符"
    
    return True, ""


def validate_profile(profile: str) -> Tuple[bool, str]:
    """
    验证个人简介
    
    Returns:
        (是否有效, 错误信息)
    """
    if len(profile) > 200:
        return False, "简介长度不能超过200字符"
    
    return True, ""


def validate_message_content(content: str) -> Tuple[bool, str]:
    """
    验证消息内容
    
    Returns:
        (是否有效, 错误信息)
    """
    if not content:
        return False, "消息内容不能为空"
    
    if len(content) > 1000:
        return False, "消息内容不能超过1000字符"
    
    return True, ""
