import math

def calculate_credits(total_bytes: int) -> int:
    """
    Calculate the number of credits required to recover a given amount of bytes.
    Formula: ceil(total_bytes / 1_073_741_824)
    For 0 or negative bytes, returns 0.
    """
    if total_bytes <= 0:
        return 0
    return math.ceil(total_bytes / 1_073_741_824)
