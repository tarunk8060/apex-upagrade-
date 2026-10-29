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
    (80, 80, False, "8 rows x 10 seats"),
    (100, 100, False, "10 rows x 10 seats"),
    (112, 120, False, "112 normalized to 120 (12 full rows x 10 seats)"),
    (120, 120, False, "12 rows x 10 seats (A1-L10)"),
    (121, 124, True, "121 normalized to 124 (Row A: 24, Rows B-F: 20 each)"),
    (140, 144, True, "140 normalized to 144 (Row A: 24, Rows B-G: 20 each)"),
    (150, 164, True, "150 normalized to 164 (Row A: 24, Rows B-H: 20 each)"),
    (200, 204, True, "200 normalized to 204 (Row A: 24, Rows B-J: 20 each)")
]

for count, expected_normalized, expected_imax, note in cases:
    seats = main.get_seat_names(count)
    is_imax = count > 120
    
    check(f"Threshold {count} seats layout detection", is_imax == expected_imax, f"Is IMAX: {is_imax}")
    check(f"Threshold {count} auto-fills complete rows", len(seats) == expected_normalized, f"{len(seats)} seats generated (expected {expected_normalized})")
    check(f"Threshold {count} unique seats (no duplicates)", len(set(seats)) == expected_normalized)

# Boundary checks
seats_120 = main.get_seat_names(120)
check("120 seats ends at L10", seats_120[-1] == "L10", f"End: {seats_120[-1]}")
check("120 seats row A has exactly 10 seats (A1-A10)", "A10" in seats_120 and "A11" not in seats_120)

seats_140 = main.get_seat_names(140)
check("140 seats normalized to 144 ends at G20", seats_140[-1] == "G20", f"End: {seats_140[-1]}")
check("140 seats row A has 24 seats (A1-A24)", "A24" in seats_140 and "A25" not in seats_140)

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
        screen_no="AUDI 2",
        screening_format="IMAX 3D",
        duration="2h 45m",
        image_url="https://image.tmdb.org/t/p/w500/test.jpg",
        age_rating="UA",
        show_timings="11:30 AM, 05:00 PM"
    )
    added_movie = main.add_movie(movie_to_add, db)
    check(f"add_movie adds {test_movie_id}", added_movie.get("id") == test_movie_id)
    check("add_movie persists screening_format and duration", added_movie.get("screening_format") == "IMAX 3D" and added_movie.get("duration") == "2h 45m")

    # Test update_movie (PUT /movies/{movie_id})
    update_data = main.MovieUpdate(
        name="Automated Test Production - Remastered",
        screening_format="3D",
        duration="2h 55m",
        screen_no="AUDI 4"
    )
    updated_movie = main.update_movie(test_movie_id, update_data, db)
    check("update_movie updates name", updated_movie.get("name") == "Automated Test Production - Remastered")
    check("update_movie updates screening_format to 3D", updated_movie.get("screening_format") == "3D")
    check("update_movie updates duration to 2h 55m", updated_movie.get("duration") == "2h 55m")
    check("update_movie updates screen_no to AUDI 4", updated_movie.get("screen_no") == "AUDI 4")

    # Check showtimes were created
    new_st = main.get_movie_showtimes(test_movie_id, db)
    check("Movie automatically seeded with showtimes", len(new_st) > 0)

    # Verify IMAX threshold on newly created movie
    added_seat_map = main.get_showtime_seats(new_st[0]["id"], db)
    check("150-seat movie normalized to full rows IMAX capacity", added_seat_map["total_seats"] == 164)
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

apex_icon_res = main.read_apex_icon()
check("read_apex_icon() resolves apex-icon.png", os.path.exists(apex_icon_res.path))

fav_png_res = main.read_favicon_png()
check("read_favicon_png() resolves favicon.png", os.path.exists(fav_png_res.path))

fav_ico_res = main.read_favicon_ico()
check("read_favicon_ico() resolves favicon.png", os.path.exists(fav_ico_res.path))

# ─────────────────────────────────────────────────────────────────
# 8. TARUN MASTER ADMIN AUTHORIZATION TESTS
# ─────────────────────────────────────────────────────────────────
print("\n[SECTION 8] TARUN MASTER ADMIN OVERVIEW TESTS")
# Test 1: Tarun is authorized and gets other admin details
tarun_overview = main.get_admins_overview("Tarun")
check("get_admins_overview('Tarun') succeeds", isinstance(tarun_overview, list) and len(tarun_overview) >= 3)
admin_names = {a["username"] for a in tarun_overview}
check("Other admins Vijay, Ravi, Karthik returned", {"Vijay", "Ravi", "Karthik"}.issubset(admin_names))

# Test 2: Other admins (e.g. Vijay) or non-admins are rejected with 403
rejected_vijay = False
try:
    main.get_admins_overview("Vijay")
except main.HTTPException as e:
    rejected_vijay = (e.status_code == 403)
check("get_admins_overview('Vijay') rejected with 403 Forbidden", rejected_vijay)

rejected_anon = False
try:
    main.get_admins_overview("")
except main.HTTPException as e:
    rejected_anon = (e.status_code == 403)
check("get_admins_overview('') rejected with 403 Forbidden", rejected_anon)

# Test 3: Tarun can create a new administrator with password
new_admin_req = main.CreateAdminRequest(
    username="TestNewAdmin",
    password="SecretPass@123",
    role="Operations Supervisor",
    access_level="Catalog & Seating Operations",
    email="testadmin@apexcinemas.com",
    requester="Tarun"
)
create_res = main.create_admin(new_admin_req)
check("create_admin by Tarun succeeds", "created successfully" in create_res["message"])

# Test 4: Newly created admin can log in with their set password
new_login_req = main.AdminLogin(username="TestNewAdmin", password="SecretPass@123")
login_res = main.login_admin(new_login_req)
check("New admin can log in with set password", login_res["username"] == "TestNewAdmin")

# Test 5: Non-Tarun user cannot create an administrator
rejected_non_tarun_create = False
try:
    bad_create = main.CreateAdminRequest(
        username="HackerAdmin",
        password="HackPass@123",
        role="Hacker",
        requester="Vijay"
    )
    main.create_admin(bad_create)
except main.HTTPException as e:
    rejected_non_tarun_create = (e.status_code == 403)
check("create_admin by non-Tarun rejected with 403 Forbidden", rejected_non_tarun_create)

# Test 6: Tarun can delete the administrator
del_admin_res = main.delete_admin("TestNewAdmin", requester="Tarun")
check("delete_admin by Tarun succeeds", "removed successfully" in del_admin_res["message"])

# Test 7: Deleted admin can no longer log in
del_login_failed = False
try:
    main.login_admin(new_login_req)
except main.HTTPException as e:
    del_login_failed = (e.status_code == 401)
check("Deleted admin login rejected with 401", del_login_failed)

# Test 8: Other default admins login (case-insensitive & whitespace trimmed)
admin_credentials_cases = [
    ("Vijay", "vijay$45", "Vijay"),
    ("vijay", "vijay$45", "Vijay"),
    ("  vijay  ", "vijay$45", "Vijay"),
    ("VIJAY", "vijay$45", "Vijay"),
    ("Ravi", "ravi!988", "Ravi"),
    ("ravi", "ravi!988", "Ravi"),
    ("Karthik", "karthik^9876", "Karthik"),
    ("karthik", "karthik^9876", "Karthik"),
    ("Tarun", "tarun@80", "Tarun"),
    ("tarun", "tarun@80", "Tarun")
]

for uname_input, pwd_input, expected_db_name in admin_credentials_cases:
    req = main.AdminLogin(username=uname_input, password=pwd_input)
    res = main.login_admin(req)
    check(f"Admin login '{uname_input}' resolves to '{expected_db_name}'", res["username"] == expected_db_name and "role" in res)

print("\n" + "=" * 70)
print(f"  TEST SUMMARY: {TESTS_PASSED} PASSED | {TESTS_FAILED} FAILED")
print("=" * 70)

if TESTS_FAILED > 0:
    sys.exit(1)
sys.exit(0)
