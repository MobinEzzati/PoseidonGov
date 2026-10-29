from app.db import get_db

conn = get_db()
cur = conn.cursor()

# STEP A: look at 3 rows of each table, so you know what is inside
cur.execute("SELECT old_award_id, next_award_id, retained FROM recompete_training LIMIT 3")
print("STEP A1: recompete_training (one row per pair)")
for row in cur.fetchall():
    print("  ", row)

cur.execute("SELECT award_id, vendor_uei, end_date FROM award_history LIMIT 3")
print("STEP A2: award_history (one row per contract)")
for row in cur.fetchall():
    print("  ", row)

# STEP B: join. For each pair, look up the old contract's end date.
cur.execute("""
    SELECT recompete_training.old_award_id,
           award_history.end_date,
           recompete_training.retained
    FROM recompete_training
    JOIN award_history
      ON award_history.award_id = recompete_training.old_award_id
    LIMIT 5
""")
print("STEP B: each pair with the old contract's end date")
for row in cur.fetchall():
    print("  ", row)

# STEP C: same join, but keep only the YEAR of the end date
cur.execute("""
    SELECT EXTRACT(YEAR FROM award_history.end_date) AS end_year,
           recompete_training.retained
    FROM recompete_training
    JOIN award_history
      ON award_history.award_id = recompete_training.old_award_id
    LIMIT 5
""")
print("STEP C: year and retained, one row per pair")
for row in cur.fetchall():
    print("  ", row)

# STEP D: group the rows by year and count them
cur.execute("""
    SELECT EXTRACT(YEAR FROM award_history.end_date) AS end_year,
           COUNT(*) AS pairs
    FROM recompete_training
    JOIN award_history
      ON award_history.award_id = recompete_training.old_award_id
    GROUP BY EXTRACT(YEAR FROM award_history.end_date)
    ORDER BY end_year
""")
print("STEP D: number of pairs per year")
for row in cur.fetchall():
    print("  ", row)

# STEP E: add the share retained, using CASE (1 if retained, else 0)
cur.execute("""
    SELECT EXTRACT(YEAR FROM award_history.end_date) AS end_year,
           COUNT(*) AS pairs,
           SUM(CASE WHEN recompete_training.retained THEN 1 ELSE 0 END) AS kept
    FROM recompete_training
    JOIN award_history
      ON award_history.award_id = recompete_training.old_award_id
    GROUP BY EXTRACT(YEAR FROM award_history.end_date)
    ORDER BY end_year
""")
print("STEP E: year, pairs, kept")
for year, pairs, kept in cur.fetchall():
    share = kept / pairs
    note = "  <-- under 30 pairs" if pairs < 30 else ""
    print(f"   {int(year)}  pairs={pairs}  kept={kept}  share={share:.0%}{note}")

conn.close()