import sqlite3, os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for db_name in ["movie.db", "booked_seats.db"]:
    db_file = os.path.join(BASE_DIR, db_name)
    if not os.path.exists(db_file):
        print(f"\n{db_name} — NOT FOUND")
        continue

    print(f"\n=== {db_name} ===")
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cur.fetchall()]

    for t in tables:
        cur.execute(f"SELECT COUNT(*) FROM [{t}]")
        count = cur.fetchone()[0]
        cur.execute(f"PRAGMA table_info([{t}])")
        cols = [c[1] for c in cur.fetchall()]
        print(f"  [{t}] — {count} rows")
        print(f"    Columns: {cols}")

    conn.close()
