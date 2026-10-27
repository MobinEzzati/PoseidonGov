from contextlib import contextmanager

from fastapi import HTTPException

from app.db import get_db
from ml.risk_scoring import company_exists


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
