import logging

from fastapi import APIRouter, HTTPException

from app.deps import db_cursor, require_company
from ml.memo_agent import generate_memo, parse_memo

logger = logging.getLogger("poseidongov")

router = APIRouter(prefix="/companies")


@router.get("/{company_name}/memo")
def get_memo(company_name: str):
    with db_cursor() as cur:
        require_company(cur, company_name)
        try:
            memo_text = generate_memo(cur, company_name)
        except Exception:
            logger.exception("Memo generation failed for %s", company_name)
            raise HTTPException(status_code=502, detail="Memo generation failed")
    return parse_memo(memo_text)
