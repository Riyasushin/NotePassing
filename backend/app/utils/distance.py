"""Distance calculation utilities based on RSSI."""
import math


def estimate_distance(rssi: int, tx_power: int = -59) -> float:
    """
    Estimate distance based on RSSI value.
    
    Uses a simplified path loss model for BLE advertisements.
    Reference: RSSI -65 approximately equals 2.5 meters.
    
    Args:
        rssi: Received Signal Strength Indicator in dBm (negative value)
        tx_power: RSSI at 1 meter distance (default -59 dBm)
    
    Returns:
        Estimated distance in meters
    """
    if rssi >= 0:
        return 0.0
    
    # Simple path loss model
    # Distance = 10 ^ ((tx_power - rssi) / (10 * n))
    # where n is path loss exponent (typically 2 for free space, 2-4 for indoors)
    
    ratio = (tx_power - rssi) / (10 * 2.5)  # Using 2.5 as path loss exponent
    distance = math.pow(10, ratio)
    
    # Clamp to reasonable range
    return round(min(max(distance, 0.1), 100.0), 1)


def rssi_to_distance_simple(rssi: int) -> float:
    """
    Simple RSSI to distance conversion.
    
    Args:
        rssi: RSSI value in dBm
    
    Returns:
        Estimated distance in meters
    """
    # Very rough approximation
    # -40 dBm: ~1m
    # -60 dBm: ~5m
    # -80 dBm: ~20m
    
    if rssi > -50:
        return 1.0
    elif rssi > -60:
        return 2.5
    elif rssi > -70:
        return 5.0
    elif rssi > -80:
        return 10.0
    else:
        return 20.0
