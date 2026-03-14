"""
临时ID生成器 - 生成和验证临时ID
"""

import hashlib
import secrets
import time
from datetime import datetime, timedelta
from typing import Tuple


def generate_temp_id(device_id: str, secret_key: str) -> Tuple[str, datetime]:
    """
    生成新的临时ID
    
    Args:
        device_id: 设备ID
        secret_key: 服务器密钥
        
    Returns:
        (临时ID, 过期时间)
    """
    timestamp = str(int(time.time()))
    random_salt = secrets.token_hex(8)
    
    # 生成哈希值
    data = f"{device_id}:{secret_key}:{timestamp}:{random_salt}"
    temp_id = hashlib.sha256(data.encode()).hexdigest()[:32]
    
    # 5分钟后过期
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    
    return temp_id, expires_at


def generate_temp_id_simple(device_id: str) -> Tuple[str, datetime]:
    """
    简化版临时ID生成（用于测试）
    
    Args:
        device_id: 设备ID
        
    Returns:
        (临时ID, 过期时间)
    """
    # 使用随机数生成32字符十六进制字符串
    temp_id = secrets.token_hex(16)
    
    # 5分钟后过期
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    
    return temp_id, expires_at
