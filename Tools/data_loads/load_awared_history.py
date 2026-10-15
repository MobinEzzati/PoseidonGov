# load_awared_history.py  (v3)
import os, time, calendar, itertools, logging
import requests
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from tqdm import tqdm          # pip install tqdm

load_dotenv()

API = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
CAP = 10000

FISCAL_YEARS = range(2014, 2024)
NAICS_CODES = ["336411", "336412", "336413", "488190", "488111"]
AGENCIES = [
    "Department of Defense",
    "National Aeronautics and Space Administration",
    "Department of Transportation",
]
FIELDS = [
    "Award ID", "Recipient Name", "Recipient UEI", "Start Date", "End Date",
    "Award Amount", "Awarding Agency", "Awarding Sub Agency",
    "NAICS", "PSC", "Description",
]

# Only load contracts at/above this dollar floor. Our matching ignores
# anything under $250k anyway, so loading smaller awards is wasted work
# and is what pushes big slices over the 10,000-row cap.
MIN_AWARD_AMOUNT = 250000

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("load_award_history.log")],
)
log = logging.getLogger("loader")

DB_HOST = os.environ.get("DB_HOST", "poseidongov-db.cf6s0y8eqhz4.us-east-1.rds.amazonaws.com")
DB_USER = os.environ.get("DB_USER", "poseidon")

def get_conn():
    return psycopg2.connect(
        host=DB_HOST, port=5432, dbname="poseidon", user=DB_USER,
        password=os.environ["DB_PASSWORD"], sslmode="require", connect_timeout=10,
        keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5,
    )

def code_of(x):
    return x.get("code") if isinstance(x, dict) else x

def fetch_page(fy, naics, agency, page, start=None, end=None):
    body = {
        "filters": {
            "award_type_codes": ["A", "B", "C", "D"],
            "time_period": [{
                "start_date": start or f"{fy - 1}-10-01",
                "end_date": end or f"{fy}-09-30",
            }],
            "award_amounts": [{"lower_bound": MIN_AWARD_AMOUNT}],
            "naics_codes": {"require": [naics]},
            "agencies": [{"type": "awarding", "tier": "toptier", "name": agency}],
        },
        "fields": FIELDS, "page": page, "limit": 100,
        "sort": "Award Amount", "order": "desc",
    }
    for attempt in range(5):
        try:
            r = requests.post(API, json=body, timeout=60)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"{r.status_code}: {r.text[:300]}")
        except requests.RequestException:
            time.sleep(2 ** attempt)
    raise RuntimeError("Too many API retries")

def to_row(r):
    award_id = r.get("generated_internal_id") or r.get("internal_id")
    return (
        str(award_id), r.get("Recipient Name"), r.get("Recipient UEI"),
        r.get("Awarding Agency"), r.get("Awarding Sub Agency"),
        code_of(r.get("NAICS")), code_of(r.get("PSC")),
        (r.get("Description") or "")[:1000],
        r.get("Start Date") or None, r.get("End Date") or None,
        r.get("Award Amount"),
    )

INSERT = """
INSERT INTO award_history
 (award_id, vendor_name, vendor_uei, awarding_agency, awarding_sub_agency,
  naics_code, psc_code, description, start_date, end_date, total_value)
VALUES %s
ON CONFLICT (award_id) DO NOTHING
"""

MARK = """
INSERT INTO load_progress (fy, naics, agency, rows_loaded, status, error)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (fy, naics, agency) DO UPDATE
SET rows_loaded = EXCLUDED.rows_loaded, status = EXCLUDED.status,
    error = EXCLUDED.error, finished_at = now()
"""

def month_windows(fy):
    out, y, m = [], fy - 1, 10
    for _ in range(12):
        last = calendar.monthrange(y, m)[1]
        out.append((f"{y}-{m:02d}-01", f"{y}-{m:02d}-{last}"))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out

def load_window(cur, fy, naics, agency, start=None, end=None):
    page, n = 1, 0
    while True:
        data = fetch_page(fy, naics, agency, page, start, end)
        results = data.get("results", [])
        if results:
            execute_values(cur, INSERT, [to_row(r) for r in results])
            n += len(results)
        if not data.get("page_metadata", {}).get("hasNext"):
            break
        page += 1
        time.sleep(0.3)
    return n

def process_slice(conn, fy, naics, agency):
    with conn.cursor() as cur:
        n = load_window(cur, fy, naics, agency)
        capped = n >= CAP
        if capped:
            n = 0
            for s, e in month_windows(fy):
                m = load_window(cur, fy, naics, agency, s, e)
                n += m
                if m >= CAP:
                    log.warning(f"still capped: FY{fy} {naics} {agency} {s}")
        cur.execute(MARK, (fy, naics, agency, n, "done", None))
    conn.commit()                      # rows + checkpoint commit together
    return n, capped

def main():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS load_progress (
                fy integer, naics text, agency text, rows_loaded integer,
                status text, error text, finished_at timestamptz DEFAULT now(),
                PRIMARY KEY (fy, naics, agency))""")
        cur.execute("SELECT fy, naics, agency FROM load_progress WHERE status = 'done'")
        done = set(cur.fetchall())
    conn.commit()

    combos = list(itertools.product(FISCAL_YEARS, NAICS_CODES, AGENCIES))
    log.info(f"{len(combos)} slices, {len(done)} already done, floor ${MIN_AWARD_AMOUNT:,}")

    for fy, naics, agency in tqdm(combos, desc="Slices"):
        if (fy, naics, agency) in done:
            continue
        for attempt in range(4):
            try:
                n, capped = process_slice(conn, fy, naics, agency)
                log.info(f"OK FY{fy} {naics} {agency[:20]}: {n} rows"
                         f"{' (split by month)' if capped else ''}")
                break
            except psycopg2.Error as e:                 # connection / DB problem
                log.warning(f"DB error on FY{fy} {naics} {agency[:20]} "
                            f"(attempt {attempt + 1}): {e}")
                try:
                    conn.close()
                except Exception:
                    pass
                time.sleep(5 * (attempt + 1))
                conn = get_conn()
            except Exception as e:                      # API problem
                conn.rollback()
                log.error(f"FAIL FY{fy} {naics} {agency[:20]}: {e}")
                with conn.cursor() as cur:
                    cur.execute(MARK, (fy, naics, agency, 0, "failed", str(e)[:500]))
                conn.commit()
                break
        else:
            log.error(f"Gave up on FY{fy} {naics} {agency[:20]} after 4 DB retries")
    conn.close()
    log.info("Finished.")

if __name__ == "__main__":
    main()