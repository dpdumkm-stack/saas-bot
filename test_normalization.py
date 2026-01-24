import sys
import os
import re

# Mock app.utils.normalize_phone_number
def normalize_phone_number(phone: str, validate_indonesia: bool = False) -> str:
    if not phone:
        return "" if not validate_indonesia else None
    digits = re.sub(r'\D', '', str(phone))
    if digits.startswith('0'):
        digits = '62' + digits[1:]
    elif digits.startswith('8'):
        digits = '62' + digits
    if validate_indonesia:
        if len(digits) < 11 or len(digits) > 15:
            return None
        if not digits.startswith('628'):
            return None
    return digits

test_cases = [
    ("0812345678", "62812345678", True),
    ("+62812345678", "62812345678", True),
    ("62812345678", "62812345678", True),
    ("812345678", "62812345678", True),
    ("081-234-5678", "62812345678", True),
    ("62 812 3456 78", "62812345678", True),
    ("021-1234567", None, True), # Invalid (Jakarta landline)
    ("12345", None, True), # Too short
    ("+1-555-0123", "15550123", False), # International (no validation)
]

print("=== STARTING NORMALIZATION TESTS ===")
all_passed = True
for inp, expected, validate in test_cases:
    result = normalize_phone_number(inp, validate_indonesia=validate)
    status = "PASS" if result == expected else "FAIL"
    if result != expected:
        all_passed = False
    print(f"[{status}] Input: {inp:<20} | Full: {str(result):<15} | Expected: {expected}")

if all_passed:
    print("\nALL TESTS PASSED! Logic is robust.")
else:
    print("\nSOME TESTS FAILED! Please review the logic.")
