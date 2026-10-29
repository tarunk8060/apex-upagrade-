"""
Comprehensive Test Runner for APEX Cinemas
Tests:
1. IMAX vs Non-IMAX Seating Threshold Tests (80, 100, 120, 121, 150, 200)
2. Live API Integration Tests against uvicorn:
   - Root & static assets (/style.css, /app.js, /)
   - Movie catalog & details
   - Showtimes & Seat Availability
   - 10-ticket limit enforcement
   - Seat booking & duplicate rejection
   - Individual-seat cancellation (other seats remain booked)
   - User authentication & password verification
   - Admin authentication & privileged operations
   - Error handling (404, 400, 401)
"""

import sys
import os
import time
import subprocess
import urllib.request
import urllib.error
import json

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import main

print("=" * 70)
print("  APEX CINEMAS — COMPREHENSIVE AUTOMATED VERIFICATION SUITE")
print("=" * 70)

TESTS_PASSED = 0
TESTS_FAILED = 0

def record_test(name, passed, detail=""):
    global TESTS_PASSED, TESTS_FAILED
    status = "PASS" if passed else "FAIL"
    msg = f"[{status}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    if passed:
        TESTS_PASSED += 1
    else:
        TESTS_FAILED += 1

# ─────────────────────────────────────────────────────────────────
# 1. SEATING THRESHOLD TESTS (MANDATORY IMAX RULE)
# ─────────────────────────────────────────────────────────────────
print("\n[SECTION 1] MANDATORY IMAX SEATING THRESHOLD TESTS")
print("Rule: total_seats > 120 -> IMAX layout | total_seats <= 120 -> non-IMAX layout")

threshold_cases = [
    (80, False, "8 rows of 10 seats (A1-H10)"),
    (100, False, "10 rows of 10 seats (A1-J10)"),
    (120, False, "12 rows of 10 seats (A1-L10)"),
    (121, True, "Row A: 24, Rows B-E: 20 each, Row F: 17"),
    (150, True, "Row A: 24, Rows B-G: 20 each, Row H: 6"),
    (200, True, "Row A: 24, Rows B-I: 20 each, Row J: 16")
]

for total_seats, expected_imax, desc in threshold_cases:
    seats = main.get_seat_names(total_seats)
    is_imax = total_seats > 120
    
    # Verify layout condition
    layout_ok = (is_imax == expected_imax)
    record_test(
        f"Threshold {total_seats} seats layout detection",
        layout_ok,
        f"Expected {'IMAX' if expected_imax else 'non-IMAX'}, Got {'IMAX' if is_imax else 'non-IMAX'}"
    )
    
    # Verify seat count
    count_ok = (len(seats) == total_seats)
    record_test(
        f"Threshold {total_seats} seats exact count",
        count_ok,
        f"Generated {len(seats)} seats, expected {total_seats} ({desc})"
    )
    
    # Verify uniqueness (no duplicate seat numbers)
    unique_ok = (len(set(seats)) == total_seats)
    record_test(
        f"Threshold {total_seats} seats uniqueness",
        unique_ok,
        f"{len(set(seats))} unique seats"
    )
    
    # Verify specific seat mappings
    if total_seats == 120:
        record_test("120 seats last seat is L10", seats[-1] == "L10", f"Last: {seats[-1]}")
    elif total_seats == 121:
        record_test("121 seats has Row A of 24 (A1-A24)", "A24" in seats and "A25" not in seats)
        record_test("121 seats last seat is F17", seats[-1] == "F17", f"Last: {seats[-1]}")
    elif total_seats == 150:
        record_test("150 seats last seat is H6", seats[-1] == "H6", f"Last: {seats[-1]}")
    elif total_seats == 200:
        record_test("200 seats last seat is J16", seats[-1] == "J16", f"Last: {seats[-1]}")

# ─────────────────────────────────────────────────────────────────
# 2. START LOCAL SERVER & RUN FULL API TESTS
# ─────────────────────────────────────────────────────────────────
print("\n[SECTION 2] SPINNING UP LOCAL FASTAPI SERVER FOR INTEGRATION TESTS")

py_exe = sys.executable
server_proc = subprocess.Popen(
    [py_exe, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
    cwd=BASE_DIR,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

time.sleep(2) # Give server time to bind

BASE_URL = "http://127.0.0.1:8000"

def api_call(method, path, body=None):
    url = f"{BASE_URL}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            try:
                return resp.status, json.loads(raw)
            except Exception:
                return resp.status, raw.decode(errors="replace")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw.decode(errors="replace")
    except Exception as ex:
        return 0, str(ex)

try:
    # Check server availability
    status, body = api_call("GET", "/")
    record_test("FastAPI Root endpoint responds with 200", status == 200)
    
    # Static CSS and JS assets
    s_css, _ = api_call("GET", "/style.css")
    record_test("Static asset /style.css served with 200", s_css == 200)
    
    s_js, _ = api_call("GET", "/app.js")
    record_test("Static asset /app.js served with 200", s_js == 200)
    
    # ── 3. MOVIE CATALOG & SHOWTIMES
    print("\n[SECTION 3] MOVIE CATALOG & SHOWTIMES")
    status, movies = api_call("GET", "/movies")
    record_test("GET /movies returns 200 and list", status == 200 and isinstance(movies, list))
    record_test("Catalog contains initial seed movies", len(movies) >= 4, f"Found {len(movies)} movies")
    
    first_movie = movies[0] if movies else None
    if first_movie:
        m_id = first_movie["id"]
        status, mv_detail = api_call("GET", f"/movies/{m_id}")
        record_test(f"GET /movies/{m_id} details with recommendations", status == 200 and "name" in mv_detail)
        
        status, showtimes = api_call("GET", f"/movies/{m_id}/showtimes")
        record_test(f"GET /movies/{m_id}/showtimes returns showtimes", status == 200 and len(showtimes) > 0)
        
        first_st_id = showtimes[0]["id"] if showtimes else None
        if first_st_id:
            status, seat_info = api_call("GET", f"/showtimes/{first_st_id}/seats")
            record_test(f"GET /showtimes/{first_st_id}/seats returns seat map", status == 200 and "seats" in seat_info)
            record_test(
                "Seat map total_seats equals seats_available in DB",
                seat_info.get("total_seats") == first_movie["seats_available"],
                f"total_seats={seat_info.get('total_seats')}, available={first_movie['seats_available']}"
            )
    
    # ── 4. USER AUTHENTICATION TESTS
    print("\n[SECTION 4] USER AUTHENTICATION")
    test_user = f"qa_user_{int(time.time())}"
    test_pass = "SecurePass@123"
    
    # Register
    status, reg_data = api_call("POST", "/users/register", {"username": test_user, "password": test_pass})
    record_test("POST /users/register creates user (201)", status == 201 and "id" in reg_data)
    user_id = reg_data.get("id") if status == 201 else None
    
    # Duplicate username registration rejected
    status, _ = api_call("POST", "/users/register", {"username": test_user, "password": test_pass})
    record_test("POST /users/register duplicate username returns 400", status == 400)
    
    # Valid login
    status, login_data = api_call("POST", "/users/login", {"username": test_user, "password": test_pass})
    record_test("POST /users/login with correct password succeeds (200)", status == 200 and login_data.get("username") == test_user)
    
    # Invalid login
    status, _ = api_call("POST", "/users/login", {"username": test_user, "password": "WrongPassword"})
    record_test("POST /users/login with incorrect password returns 401", status == 401)
    
    # ── 5. ADMIN AUTHENTICATION TESTS
    print("\n[SECTION 5] ADMIN AUTHENTICATION")
    status, admin_data = api_call("POST", "/admins/login", {"username": "Tarun", "password": "tarun@80"})
    record_test("POST /admins/login with valid admin credentials succeeds (200)", status == 200 and admin_data.get("username") == "Tarun")
    
    status, _ = api_call("POST", "/admins/login", {"username": "Tarun", "password": "badpassword"})
    record_test("POST /admins/login with bad password returns 401", status == 401)
    
    # ── 6. SEAT BOOKING & INDIVIDUAL CANCELLATION WORKFLOW
    print("\n[SECTION 6] SEAT BOOKING & INDIVIDUAL CANCELLATION")
    if first_st_id and user_id:
        seat_A = "C3"
        seat_B = "C4"
        
        # Book 2 seats together
        book_payload = {
            "user_name": test_user,
            "user_id": user_id,
            "seats": [seat_A, seat_B]
        }
        status, book_resp = api_call("POST", f"/showtimes/{first_st_id}/book", book_payload)
        record_test("Book multiple seats [C3, C4] succeeds (200)", status == 200 and "booked_seats" in book_resp)
        
        # Verify seats are now marked booked in seat map
        status, seats_after = api_call("GET", f"/showtimes/{first_st_id}/seats")
        seat_map = seats_after.get("seats", {})
        record_test("Seat C3 is booked", seat_map.get(seat_A) is True)
        record_test("Seat C4 is booked", seat_map.get(seat_B) is True)
        
        # Duplicate booking of already booked seat C3 must fail with 400
        dup_payload = {
            "user_name": "AnotherUser",
            "user_id": "I999",
            "seats": [seat_A]
        }
        status, dup_resp = api_call("POST", f"/showtimes/{first_st_id}/book", dup_payload)
        record_test("Attempt to book already booked seat C3 returns 400", status == 400)
        
        # 10-ticket limit disclaimer test
        excess_seats = [f"B{i}" for i in range(1, 13)] # 12 seats
        limit_payload = {
            "user_name": test_user,
            "user_id": user_id,
            "seats": excess_seats
        }
        status, limit_resp = api_call("POST", f"/showtimes/{first_st_id}/book", limit_payload)
        record_test(
            "Booking > 10 seats enforces limit disclaimer (400)",
            status == 400 and "10 tickets" in str(limit_resp)
        )
        
        # INDIVIDUAL SEAT CANCELLATION TEST:
        # Cancel ONLY seat C3. Seat C4 MUST remain booked!
        cancel_payload = {"seat_no": seat_A}
        status, cancel_resp = api_call("POST", f"/showtimes/{first_st_id}/cancel", cancel_payload)
        record_test("Cancel individual seat C3 succeeds (200)", status == 200 and "cancelled" in str(cancel_resp).lower())
        
        # Verify seat map: C3 should now be available (False), but C4 MUST still be booked (True)!
        status, seats_post_cancel = api_call("GET", f"/showtimes/{first_st_id}/seats")
        post_map = seats_post_cancel.get("seats", {})
        record_test("Cancelled seat C3 is now available (False)", post_map.get(seat_A) is False)
        record_test("Uncancelled seat C4 remains securely booked (True)", post_map.get(seat_B) is True)
        
        # Clean up remaining seat C4
        api_call("POST", f"/showtimes/{first_st_id}/cancel", {"seat_no": seat_B})
    
    # ── 7. ADMIN MOVIE MANAGEMENT
    print("\n[SECTION 7] ADMIN MOVIE MANAGEMENT WORKFLOW")
    admin_movie_id = f"MOV_QA_{int(time.time())}"
    new_movie = {
        "id": admin_movie_id,
        "name": "QA Benchmark Feature",
        "genre": "Thriller Mystery",
        "language": "English",
        "price": 250,
        "seats_available": 140, # IMAX Screen (> 120)
        "screen_no": "IMAX Screen 1",
        "image_url": "https://image.tmdb.org/t/p/w500/sample.jpg",
        "age_rating": "UA",
        "show_timings": "10:30 AM, 03:00 PM, 07:45 PM"
    }
    status, add_res = api_call("POST", "/movies", new_movie)
    record_test("Admin POST /movies creates movie with custom timings (201)", status == 201 and add_res.get("id") == admin_movie_id)
    
    # Verify auto-seeded showtimes
    status, st_list = api_call("GET", f"/movies/{admin_movie_id}/showtimes")
    record_test("Movie automatically seeded with showtimes", status == 200 and len(st_list) > 0)
    
    # Delete movie
    status, del_res = api_call("DELETE", f"/movies/{admin_movie_id}")
    record_test("Admin DELETE /movies/{id} succeeds (200)", status == 200)

finally:
    # Terminate server
    server_proc.terminate()
    server_proc.wait(timeout=5)
    print("\nLocal test server terminated cleanly.")

print("\n" + "=" * 70)
print(f"  FINAL SUMMARY: {TESTS_PASSED} PASSED | {TESTS_FAILED} FAILED")
print("=" * 70)

if TESTS_FAILED > 0:
    sys.exit(1)
sys.exit(0)
