# load_award_history.py
import os, time
import requests
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

API = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

# ---- The slice: edit these ----
FISCAL_YEARS = range(2014, 2024)                      # FY2014..FY2023
NAICS_CODES = ["336411", "336412", "336413", "488190", "488111"]
AGENCIES = [
    "Department of Defense",
    "National Aeronautics and Space Administration",
    "Department of Transportation",                   # includes FAA
]
# --------------------------------

FIELDS = [
    "Award ID", "Recipient Name", "Recipient UEI", "Start Date", "End Date",
    "Award Amount", "Awarding Agency", "Awarding Sub Agency",
    "NAICS", "PSC", "Description",
]

def code_of(x):
    """NAICS/PSC can come back as a dict or a plain string."""
    if isinstance(x, dict):
        return x.get("code")
    return x

def fetch_page(fy, naics, agency, page):
    body = {
        "filters": {
            "award_type_codes": ["A", "B", "C", "D"],       # contracts only
            "time_period": [{
                "start_date": f"{fy - 1}-10-01",
                "end_date": f"{fy}-09-30",
            }],
            "naics_codes": {"require": [naics]},            # if the API returns 422, try [naics]
            "agencies": [{"type": "awarding", "tier": "toptier", "name": agency}],
        },
        "fields": FIELDS,
        "page": page,
        "limit": 100,
        "sort": "Award Amount",
        "order": "desc",
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
    raise RuntimeError("Too many retries")

def to_row(r):
    # generated_internal_id is unique; "Award ID" (the PIID) is NOT unique across agencies
    award_id = r.get("generated_internal_id") or r.get("internal_id")
    return (
        str(award_id),
        r.get("Recipient Name"),
        r.get("Recipient UEI"),
        r.get("Awarding Agency"),
        r.get("Awarding Sub Agency"),
        code_of(r.get("NAICS")),
        code_of(r.get("PSC")),
        (r.get("Description") or "")[:1000],
        r.get("Start Date") or None,
        r.get("End Date") or None,
        r.get("Award Amount"),
    )

INSERT = """
INSERT INTO award_history
 (award_id, vendor_name, vendor_uei, awarding_agency, awarding_sub_agency,
  naics_code, psc_code, description, start_date, end_date, total_value)
VALUES %s
ON CONFLICT (award_id) DO NOTHING
"""

def main():
    conn = psycopg2.connect(
        host=os.environ["DB_HOST"], port=5432, dbname="poseidon",
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"],
        sslmode="require", connect_timeout=10,
    )
    total = 0
    try:
        with conn.cursor() as cur:
            for fy in FISCAL_YEARS:
                for naics in NAICS_CODES:
                    for agency in AGENCIES:
                        page, n = 1, 0
                        while True:
                            data = fetch_page(fy, naics, agency, page)
                            results = data.get("results", [])
                            if results:
                                rows = [to_row(r) for r in results]
                                execute_values(cur, INSERT, rows)
                                n += len(rows)
                            if not data.get("page_metadata", {}).get("hasNext"):
                                break
                            page += 1
                            time.sleep(0.3)               # be polite to the API
                        conn.commit()
                        total += n
                        print(f"FY{fy} {naics} {agency[:25]:25} -> {n} rows")
    finally:
        conn.close()
    print(f"Done. Processed {total} rows (duplicates skipped).")

if __name__ == "__main__":
    main()