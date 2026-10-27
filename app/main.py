import logging
import sys
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException

sys.path.append("..")
from app.db import get_db
from ML.risk_scoring import (
    company_exists,
    compute_hhi,
    compute_recompete_risk,
    get_agency_breakdown,
    interpret_hhi,
    interpret_recompete,
)
from ML.memo_agent import generate_memo, parse_memo

logger = logging.getLogger("poseidongov")

app = FastAPI(title="PoseidonGov API")


@contextmanager
def db_cursor():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            yield cur
    finally:
        conn.close()


def require_company(cur, company_name: str):
    if not company_exists(cur, company_name):
        raise HTTPException(status_code=404, detail="Company not found")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/companies")
def list_companies():
    with db_cursor() as cur:
        cur.execute("""
            SELECT recipient_name, hhi_agency, recompete_risk
            FROM risk_score
        """)
        rows = cur.fetchall()

    return {
        name: {
            "hhi": float(hhi) if hhi else None,
            "recompete_risk": float(recompete) if recompete else None,
        }
        for name, hhi, recompete in rows
    }


@app.get("/companies/{company_name}/risk")
def get_company_risk(company_name: str):
    with db_cursor() as cur:
        require_company(cur, company_name)
        hhi = compute_hhi(cur, company_name)
        recompete = compute_recompete_risk(cur, company_name)
        breakdown = get_agency_breakdown(cur, company_name)

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
                "pct": float(row[2]),
            }
            for row in breakdown
        ],
    }


@app.get("/companies/{company_name}/fleet")
def get_company_fleet(company_name: str):
    with db_cursor() as cur:
        cur.execute("""
            SELECT n_number, make_model, year_mfr
            FROM aircraft
            WHERE owner_name ILIKE %s
            ORDER BY year_mfr DESC
        """, (f"%{company_name}%",))
        rows = cur.fetchall()

    return {
        "company": company_name,
        "fleet_size": len(rows),
        "aircraft": [
            {"tail": r[0], "make_model": r[1], "year": r[2]}
            for r in rows
        ],
    }


@app.get("/companies/{company_name}/memo")
def get_memo(company_name: str):
    with db_cursor() as cur:
        require_company(cur, company_name)
        try:
            memo_text = generate_memo(cur, company_name)
        except Exception:
            logger.exception("Memo generation failed for %s", company_name)
            raise HTTPException(status_code=502, detail="Memo generation failed")
    return parse_memo(memo_text)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
