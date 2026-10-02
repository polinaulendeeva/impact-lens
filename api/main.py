from fastapi import FastAPI
from sqlalchemy import text

from app.db import SessionLocal

app = FastAPI(
    title="Impact Lens API",
    description="Read-only access to reviewed impact assessments and portfolio exposure.",
)


def rows(sql: str) -> list[dict]:
    with SessionLocal() as session:
        result = session.execute(text(sql))
        return [dict(r) for r in result.mappings()]


@app.get("/health")
def health():
    rows("SELECT 1")
    return {"status": "ok"}


@app.get("/exposure")
def exposure():
    """Portfolio exposure per theme, with review coverage."""
    return rows("SELECT * FROM v_portfolio_exposure")


@app.get("/assessments")
def assessments(status: str | None = None):
    """Latest assessment per company and theme, with the review outcome."""
    data = rows("SELECT * FROM v_current_assessment")
    if status:
        data = [r for r in data if r.get("status") == status]
    return data
    