

# here we are buildint the skeleton of our app 

from fastapi import FastAPI
import psycopg2
import sys
import os
sys.path.append("..")
from ML.risk_scoring import compute_hhi, compute_recompete_risk, interpret_hhi, interpret_recompete, get_agency_breakdown
from ML.memo_agent import generate_memo, parse_memo

app = FastAPI(title="PoseidonGov API")
def get_db():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=5432,
        dbname="poseidon",
        user=os.environ.get("DB_USER", "poseidon"),
        password=os.environ.get("DB_PASSWORD", "localdev"),
        sslmode=os.environ.get("DB_SSLMODE", "disable")
    )


@app.get("/test")
def thisTest():
    return "thsi is Test"



@app.get("/companies")
def list_companies():
    conn = get_db()
    cur = conn.cursor()
    
    res = {}
    cur.execute("""
        SELECT recipient_name, hhi_agency, recompete_risk 
        FROM risk_score
    """)
    rows = cur.fetchall()
    for row in rows:
        res[row[0]] = {
            "hhi": float(row[1]) if row[1] else None,
            "recompete_risk": float(row[2]) if row[2] else None,
        }
    
    cur.close()
    conn.close()
    return res

@app.get("/companies/{company_name}/risk")
def get_company_risk(company_name: str):
    conn = get_db()
    cur = conn.cursor()
    
    hhi = compute_hhi(cur, company_name)
    recompete = compute_recompete_risk(cur, company_name)
    breakdown = get_agency_breakdown(cur, company_name)
    
    cur.close()
    conn.close()
    
    return {
        "company": company_name,
        "hhi": round(hhi, 4),
        "hhi_label": interpret_hhi(hhi),
        "recompete_risk": round(recompete, 4),
        "recompete_label": interpret_recompete(recompete),
        "agency_breakdown": [
            {
                "agency": row[0],
                "total": float(row[1]),
                "pct": float(row[2])
            }
            for row in breakdown
        ]
    }

@app.get("/companies/{company_name}/fleet")
def get_company_fleet(company_name: str):
    conn = get_db()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT n_number, make_model, year_mfr
        FROM aircraft
        WHERE owner_name ILIKE %s
        ORDER BY year_mfr DESC
    """, (f"%{company_name}%",))
    
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    return {
        "company": company_name,
        "fleet_size": len(rows),
        "aircraft": [
            {"tail": r[0], "make_model": r[1], "year": r[2]}
            for r in rows
        ]
    }
@app.get("/companies/{company_name}/memo")
async def get_memo(company_name: str):
    print(f"DEBUG: company_name = '{company_name}'")  # add this
    conn = get_db()
    cur = conn.cursor()
    memo_text = generate_memo(cur, company_name)
    parsed = parse_memo(memo_text)
    cur.close()
    conn.close()
    return parsed
# your endpoints go here

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)