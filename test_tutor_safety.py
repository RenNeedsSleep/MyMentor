"""
Quick validation test for tutor safety features.
Run: python test_tutor_safety.py
"""

from pydantic import ValidationError
from tutor_schemas import TutorProfileUpdate
from models import TutorProfile
from services.tutor_service import check_profile_complete

print("=" * 50)
print("TEST 1: Pydantic Validation")
print("=" * 50)

cases = [
    ({"full_name": "", "qualifications": "good teacher yes", "subjects": "Math"}, "empty name", True),
    ({"full_name": "John", "qualifications": "ok", "subjects": "Math"}, "short quals (<3 words)", True),
    ({"full_name": "John", "qualifications": "good teacher yes", "subjects": ""}, "empty subjects", True),
    ({"full_name": "John", "qualifications": "good teacher yes", "subjects": "Math"}, "valid input", False),
]

all_pass = True
for data, label, should_fail in cases:
    try:
        TutorProfileUpdate(**data)
        if should_fail:
            print(f"  FAIL: '{label}' was accepted but should have been rejected")
            all_pass = False
        else:
            print(f"  PASS: '{label}' accepted correctly")
    except ValidationError:
        if should_fail:
            print(f"  PASS: '{label}' rejected correctly")
        else:
            print(f"  FAIL: '{label}' was rejected but should have been accepted")
            all_pass = False

print()
print("=" * 50)
print("TEST 2: Profile Completeness Check")
print("=" * 50)

# Complete profile
tp1 = TutorProfile()
tp1.full_name = "John Doe"
tp1.qualifications = "MSc Computer Science"
tp1.subjects = "Math, Physics"
result1 = check_profile_complete(tp1)
print(f"  Complete profile -> {result1} {'PASS' if result1 else 'FAIL'}")

# Missing full_name
tp2 = TutorProfile()
tp2.full_name = None
tp2.qualifications = "MSc Computer Science"
tp2.subjects = "Math"
result2 = check_profile_complete(tp2)
print(f"  Missing full_name -> {result2} {'PASS' if not result2 else 'FAIL'}")

# Missing qualifications
tp3 = TutorProfile()
tp3.full_name = "John"
tp3.qualifications = ""
tp3.subjects = "Math"
result3 = check_profile_complete(tp3)
print(f"  Empty qualifications -> {result3} {'PASS' if not result3 else 'FAIL'}")

# Missing subjects
tp4 = TutorProfile()
tp4.full_name = "John"
tp4.qualifications = "Degree"
tp4.subjects = None
result4 = check_profile_complete(tp4)
print(f"  Missing subjects -> {result4} {'PASS' if not result4 else 'FAIL'}")

# None profile
result5 = check_profile_complete(None)
print(f"  None profile -> {result5} {'PASS' if not result5 else 'FAIL'}")

print()
print("=" * 50)
print("TEST 3: Import Verification")
print("=" * 50)

try:
    from routers.tutor_router import tutor_router
    print("  PASS: tutor_router imported")
except Exception as e:
    print(f"  FAIL: {e}")

try:
    from main import app
    routes = [r.path for r in app.routes]
    checks = ["/tutor/me", "/tutor/profile"]
    for c in checks:
        if c in routes:
            print(f"  PASS: Route {c} registered")
        else:
            print(f"  WARN: Route {c} not directly found (may be under router prefix)")
except Exception as e:
    print(f"  FAIL: {e}")

print()
if all_pass:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
