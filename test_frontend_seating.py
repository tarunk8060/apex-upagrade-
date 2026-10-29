"""
Frontend Seating Logic Automated Verification
Simulates and tests the exact JavaScript seat generation algorithm from app.js
across all required thresholds and test cases (80, 100, 112, 120, 121, 140, 150, 200).
"""

import sys
import os
import main

print("=" * 70)
print("  FRONTEND SEATING ALGORITHM VERIFICATION")
print("=" * 70)

def get_row_letter(r):
    alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    if r < len(alphabet):
        return alphabet[r]
    first = alphabet[(r // len(alphabet)) - 1]
    second = alphabet[r % len(alphabet)]
    return f"{first}{second}"

def get_normalized_total_seats(total_seats):
    if total_seats <= 0:
        return 0
    if total_seats > 120:
        if total_seats <= 24:
            return 24
        rem = (total_seats - 24) % 20
        if rem == 0:
            return total_seats
        return total_seats + (20 - rem)
    else:
        rem = total_seats % 10
        if rem == 0:
            return total_seats
        return total_seats + (10 - rem)

def simulate_frontend_render_seat_grid(total_seats):
    """
    Exact simulation of renderSeatGrid in app.js:
    Returns the list of seat IDs generated as clickable buttons.
    """
    total_seats = get_normalized_total_seats(total_seats)
    generated_seats = []
    is_imax = total_seats > 120

    if is_imax:
        row_a_seats = min(24, total_seats)
        remaining = total_seats - row_a_seats
        remaining_rows = (remaining + 19) // 20 if remaining > 0 else 0
        total_rows = 1 + remaining_rows

        # Cinema Hierarchy: Screen at top; Row G (highest) in front, Row A at back
        for r in range(total_rows - 1, -1, -1):
            letter = get_row_letter(r)
            if r == 0:
                for col in range(1, 25):
                    if col <= row_a_seats:
                        generated_seats.append(f"A{col}")
            else:
                row_seats_remaining = (remaining - (r - 1) * 20) if (r == total_rows - 1) else 20
                seat_counter = 0
                for col in range(1, 25):
                    if col in (6, 7, 18, 19):
                        pass # Aisle spacer
                    else:
                        seat_counter += 1
                        if seat_counter <= row_seats_remaining:
                            generated_seats.append(f"{letter}{seat_counter}")
    else:
        cols = 10
        total_rows = (total_seats + cols - 1) // cols
        for r in range(total_rows - 1, -1, -1):
            letter = get_row_letter(r)
            seats_in_this_row = (total_seats - r * cols) if (r == total_rows - 1) else cols
            for c in range(cols):
                seat_num = c + 1
                if seat_num <= seats_in_this_row:
                    generated_seats.append(f"{letter}{seat_num}")

    return generated_seats

test_capacities = [80, 100, 112, 120, 121, 140, 150, 200]
all_ok = True

for cap in test_capacities:
    expected = main.get_seat_names(cap)
    frontend = simulate_frontend_render_seat_grid(cap)
    
    is_imax = cap > 120
    layout_name = "IMAX" if is_imax else "non-IMAX"
    
    norm_cap = get_normalized_total_seats(cap)
    count_matches = len(frontend) == norm_cap
    set_matches = (set(frontend) == set(expected))
    no_duplicates = len(set(frontend)) == norm_cap
    
    # Verify cinema hierarchy: highest row is first (closest to screen); Row A is at the back
    row_order_correct = frontend[-1].startswith("A")

    status = "PASS" if (count_matches and set_matches and no_duplicates and row_order_correct) else "FAIL"
    if status == "FAIL":
        all_ok = False
        
    print(f"[{status}] Input Cap {cap:3d} -> Normalized Full Rows: {norm_cap:3d} ({layout_name:8s}) -> Count: {len(frontend)} | Sets Match: {set_matches} | Row A at back: {row_order_correct}")
    if not set_matches:
        diff_missing = set(expected) - set(frontend)
        diff_extra = set(frontend) - set(expected)
        print(f"       Missing: {diff_missing} | Extra: {diff_extra}")

print("=" * 70)
if all_ok:
    print("  ALL FRONTEND SEATING TESTS PASSED! ZERO DISCREPANCIES!")
else:
    print("  SOME FRONTEND SEATING TESTS FAILED!")
    sys.exit(1)
