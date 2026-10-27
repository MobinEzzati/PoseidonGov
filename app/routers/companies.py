from fastapi import APIRouter

from app.deps import db_cursor, require_company
from ml.risk_scoring import (
    compute_hhi,
    compute_recompete_risk,
    get_agency_breakdown,
    interpret_hhi,
    interpret_recompete,
)

router = APIRouter(prefix="/companies")


@router.get("")
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


@router.get("/{company_name}/risk")
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
