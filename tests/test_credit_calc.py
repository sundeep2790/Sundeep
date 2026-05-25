import pytest
from datarescue.payments import calculate_credits

def test_credit_calc_zero_bytes():
    assert calculate_credits(0) == 0
    assert calculate_credits(-500) == 0

def test_credit_calc_one_gb():
    # exactly 1 GB
    assert calculate_credits(1_073_741_824) == 1

def test_credit_calc_one_byte_over():
    # 1 GB + 1 byte
    assert calculate_credits(1_073_741_825) == 2

def test_credit_calc_one_hundred_mb():
    # 100 MB
    bytes_100_mb = 100 * 1024 * 1024
    assert calculate_credits(bytes_100_mb) == 1

def test_credit_calc_two_point_seven_gb():
    # 2.7 GB
    bytes_2_7_gb = int(2.7 * 1_073_741_824)
    assert calculate_credits(bytes_2_7_gb) == 3
