"""
RSSI转换器 - 将蓝牙信号强度转换为距离估算
"""

import math


def rssi_to_distance(rssi: int, tx_power: int = -59, n: float = 2.0) -> float:
    """
    根据RSSI估算距离
    
    使用对数距离路径损耗模型:
    distance = 10 ^ ((tx_power - rssi) / (10 * n))
    
    Args:
        rssi: 接收信号强度指示 (dBm)
        tx_power: 1米处的参考RSSI (默认-59 dBm)
        n: 路径损耗指数 (默认2.0，自由空间)
        
    Returns:
        估算距离 (米)
    """
    # 防止除零或负数
    if n <= 0:
        n = 2.0
    
    # 计算距离
    ratio = (tx_power - rssi) / (10 * n)
    distance = math.pow(10, ratio)
    
    # 限制在合理范围内
    distance = max(0.1, min(distance, 100.0))
    
    return round(distance, 1)


def rssi_to_distance_simple(rssi: int) -> float:
    """
    简化的RSSI转距离
    
    使用经验公式:
    - RSSI -30: 约0.5米
    - RSSI -50: 约1米
    - RSSI -70: 约10米
    - RSSI -90: 约50米
    """
    # 经验映射
    if rssi >= -40:
        return 0.5
    elif rssi >= -55:
        return 1.0
    elif rssi >= -65:
        return 2.5
    elif rssi >= -75:
        return 5.0
    elif rssi >= -85:
        return 10.0
    else:
        return 20.0
