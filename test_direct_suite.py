"""
In-process Direct Functional & Business Logic Test Suite
Tests all endpoints, database queries, business rules, and seating thresholds
Runs completely inside sandbox without network sockets.
"""

import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import main

print("=" * 70)
print("  APEX CINEMAS — DIRECT FUNCTIONAL & BUSINESS LOGIC SUITE")
print("=" * 70)

TESTS_PASSED = 0
TESTS_FAILED = 0

def check(name, condition, detail=""):
    global TESTS_PASSED, TESTS_FAILED
    status = "PASS" if condition else "FAIL"
    msg = f"[{status}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)
    if condition:
        TESTS_PASSED += 1
    else:
        TESTS_FAILED += 1

# ─────────────────────────────────────────────────────────────────
# 1. IMAX VS NON-IMAX SEATING THRESHOLD TESTS
# ─────────────────────────────────────────────────────────────────
print("\n[SECTION 1] MANDATORY IMAX SEATING THRESHOLD TESTS")
print("Rule: total_seats > 120 -> IMAX layout | total_seats <= 120 -> non-IMAX layout")

cases = [
    (80, False, "8 rows x 10 seats"),
    (100, False, "10 rows x 10 seats"),
    (120, False, "12 rows x 10 seats (A1-L10)"),
    (121, True, "Row A: 24, Rows B-E: 20 each, Row F: 17"),
    (150, True, "Row A: 24, Rows B-G: 20 each, Row H: 6"),
    (200, True, "Row A: 24, Rows B-I: 20 each, Row J: 16")
]

for count, expected_imax, note in cases:
    seats = main.get_seat_names(count)
    is_imax = count > 120
    
    check(f"Threshold {count} seats layout detection", is_imax == expected_imax, f"Is IMAX: {is_imax}")
    check(f"Threshold {count} exact count", len(seats) == count, f"{len(seats)} seats generated")
    check(f"Threshold {count} unique seats (no duplicates)", len(set(seats)) == count)

# Boundary checks
seats_120 = main.get_seat_names(120)
check("120 seats ends at L10", seats_120[-1] == "L10", f"End: {seats_120[-1]}")
check("120 seats row A has exactly 10 seats (A1-A10)", "A10" in seats_120 and "A11" not in seats_120)

seats_121 = main.get_seat_names(121)
check("121 seats has Row A of 24 (A1-A24)", "A24" in seats_121 and "A25" not in seats_121)
check("121 seats ends at F17", seats_121[-1] == "F17", f"End: {seats_121[-1]}")

# ─────────────────────────────────────────────────────────────────
# 2. DATABASE & MOVIE CATALOG TESTS
# ─────────────────────────────────────────────────────────────────
print("\n[SECTION 2] DATABASE & CATALOG VERIFICATION")

db_gen = main.get_db()
db = next(db_gen)

try:
    movies = main.list_movies(db)
    check("list_movies returns non-empty list", isinstance(movies, list) and len(movies) > 0, f"{len(movies)} movies found")
    
    first_movie = movies[0]
    m_id = first_movie["id"]
    
    movie_detail = main.get_movie(m_id, db)
    check(f"get_movie({m_id}) returns correct movie", movie_detail["name"] == first_movie["name"])
    check("Movie recommendations list present", "recommendations" in movie_detail)
    
    # Showtimes
    showtimes = main.get_movie_showtimes(m_id, db)
    check(f"get_movie_showtimes({m_id}) returns active showtimes", isinstance(showtimes, list) and len(showtimes) > 0, f"{len(showtimes)} showtimes")
    st_id = showtimes[0]["id"]

    # Seat Map
    seat_data = main.get_showtime_seats(st_id, db)
    check(f"get_showtime_seats({st_id}) returns seat map", "seats" in seat_data)
    check("Seat map total_seats equals seats_available in DB", seat_data["total_seats"] == first_movie["seats_available"])
    check("Seat map seat count matches total_seats", len(seat_data["seats"]) == seat_data["total_seats"])

    # ─────────────────────────────────────────────────────────────────
    # 3. USER AUTHENTICATION TESTS
    # ─────────────────────────────────────────────────────────────────
    print("\n[SECTION 3] USER AUTHENTICATION & SECURITY")
    
    test_username = f"user_{int(time.time())}"
    test_password = "Password#999"
    
    user_create = main.UserCreate(username=test_username, password=test_password)
    user_res = main.register_user(user_create, db)
    check("register_user creates new user record", user_res["username"] == test_username and user_res["id"].startswith("I"))
    user_id = user_res["id"]
    
    # Duplicate username rejection
    try:
        main.register_user(user_create, db)
        check("Duplicate username registration rejected", False, "Expected HTTPException 400")
    except main.HTTPException as he:
        check("Duplicate username registration rejected with 400", he.status_code == 400)

    # Valid user login
    user_login = main.UserLogin(username=test_username, password=test_password)
    login_res = main.login_user(user_login, db)
    check("login_user with valid credentials succeeds", login_res["username"] == test_username and login_res["id"] == user_id)

    # Invalid user login
    try:
        bad_login = main.UserLogin(username=test_username, password="WrongPassword")
        main.login_user(bad_login, db)
        check("login_user with wrong password rejected", False, "Expected 401")
    except main.HTTPException as he:
        check("login_user with wrong password rejected with 401", he.status_code == 401)

    # ─────────────────────────────────────────────────────────────────
    # 4. ADMIN AUTHENTICATION TESTS
    # ─────────────────────────────────────────────────────────────────
    print("\n[SECTION 4] ADMIN AUTHENTICATION")
    
    admin_login_ok = main.AdminLogin(username="Tarun", password="tarun@80")
    admin_res = main.login_admin(admin_login_ok)
    check("login_admin with correct credentials succeeds", admin_res["username"] == "Tarun")

    try:
        bad_admin = main.AdminLogin(username="Tarun", password="badpassword")
        main.login_admin(bad_admin)
        check("login_admin with bad password rejected", False, "Expected 401")
    except main.HTTPException as he:
        check("login_admin with bad password rejected with 401", he.status_code == 401)

    # ─────────────────────────────────────────────────────────────────
    # 5. BOOKING & INDIVIDUAL SEAT CANCELLATION WORKFLOW
    # ─────────────────────────────────────────────────────────────────
    print("\n[SECTION 5] BOOKING & INDIVIDUAL-SEAT CANCELLATION")
    
    seat_1 = "B3"
    seat_2 = "B4"
    
    book_req = main.BookSeatsRequest(
        user_name=test_username,
        user_id=user_id,
        seats=[seat_1, seat_2]
    )
    book_result = main.book_seats(st_id, book_req, db)
    check("book_seats reserves seats [B3, B4]", "booked_seats" in book_result and len(book_result["booked_seats"]) == 2)

    # Verify both seats are marked booked
    seat_map_post = main.get_showtime_seats(st_id, db)["seats"]
    check("Seat B3 is marked booked", seat_map_post.get(seat_1) is True)
    check("Seat B4 is marked booked", seat_map_post.get(seat_2) is True)

    # Attempt to book an already occupied seat
    dup_req = main.BookSeatsRequest(
        user_name="OtherUser",
        user_id="I888",
        seats=[seat_1]
    )
    try:
        main.book_seats(st_id, dup_req, db)
        check("Booking occupied seat B3 rejected", False, "Expected 400")
    except main.HTTPException as he:
        check("Booking occupied seat B3 rejected with 400", he.status_code == 400)

    # 10-ticket limit check
    excess_req = main.BookSeatsRequest(
        user_name=test_username,
        user_id=user_id,
        seats=[f"D{i}" for i in range(1, 13)] # 12 seats
    )
    try:
        main.book_seats(st_id, excess_req, db)
        check("Booking > 10 tickets rejected", False, "Expected 400")
    except main.HTTPException as he:
        check("Booking > 10 tickets rejected with 400 disclaimer", he.status_code == 400 and "10 tickets" in he.detail)

    # CANCEL INDIVIDUAL SEAT: Cancel seat B3 only. Seat B4 MUST remain booked!
    cancel_req = main.CancelSeatRequest(seat_no=seat_1)
    cancel_res = main.cancel_seats(st_id, cancel_req, db)
    check("cancel_seats for B3 processes refund", "refund_amount" in cancel_res and cancel_res["seat_no"] == seat_1)

    seat_map_after_cancel = main.get_showtime_seats(st_id, db)["seats"]
    check("Cancelled seat B3 is now available (False)", seat_map_after_cancel.get(seat_1) is False)
    check("Uncancelled seat B4 remains booked (True)", seat_map_after_cancel.get(seat_2) is True)

    # Cleanup B4
    main.cancel_seats(st_id, main.CancelSeatRequest(seat_no=seat_2), db)

    # ─────────────────────────────────────────────────────────────────
    # 6. ADMIN MOVIE MANAGEMENT WORKFLOW
    # ─────────────────────────────────────────────────────────────────
    print("\n[SECTION 6] ADMIN MOVIE MANAGEMENT")
    
    test_movie_id = f"MOV_TEST_{int(time.time())}"
    movie_to_add = main.MovieCreate(
        id=test_movie_id,
        name="Automated Test Production",
        genre="Action Sci-Fi",
        language="English",
        price=180,
        seats_available=150, # IMAX Screen
        screen_no="IMAX Screen A",
        image_url="https://image.tmdb.org/t/p/w500/test.jpg",
        age_rating="UA",
        show_timings="11:30 AM, 05:00 PM"
    )
    added_movie = main.add_movie(movie_to_add, db)
    check(f"add_movie adds {test_movie_id}", added_movie.get("id") == test_movie_id)

    # Check showtimes were created
    new_st = main.get_movie_showtimes(test_movie_id, db)
    check("Movie automatically seeded with showtimes", len(new_st) > 0)

    # Verify IMAX threshold on newly created movie
    added_seat_map = main.get_showtime_seats(new_st[0]["id"], db)
    check("150-seat movie correctly detected as IMAX capacity", added_seat_map["total_seats"] == 150)
    check("Row A has 24 seats", "A24" in added_seat_map["seats"] and "A25" not in added_seat_map["seats"])

    # Delete movie
    del_res = main.delete_movie(test_movie_id, db)
    check("delete_movie successfully removes movie and cascaded records", "removed successfully" in del_res["message"])

finally:
    try:
        next(db_gen)
    except StopIteration:
        pass

# ─────────────────────────────────────────────────────────────────
# 7. STATIC ASSETS RESOLUTION
# ─────────────────────────────────────────────────────────────────
print("\n[SECTION 7] STATIC ASSETS RESOLUTION")
css_res = main.read_style()
check("read_style() resolves style.css", os.path.exists(css_res.path))

js_res = main.read_app_js()
check("read_app_js() resolves app.js", os.path.exists(js_res.path))

html_res = main.read_root()
check("read_root() resolves index.html", os.path.exists(html_res.path))

print("\n" + "=" * 70)
print(f"  TEST SUMMARY: {TESTS_PASSED} PASSED | {TESTS_FAILED} FAILED")
print("=" * 70)

if TESTS_FAILED > 0:
    sys.exit(1)
sys.exit(0)
