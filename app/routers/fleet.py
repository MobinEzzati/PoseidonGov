from fastapi import APIRouter

from app.deps import db_cursor

router = APIRouter(prefix="/companies")


@router.get("/{company_name}/fleet")
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
