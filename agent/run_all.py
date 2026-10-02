import sys

from sqlalchemy import select

from agent.assess import PROMPT_VERSION, assess
from agent.guardrails import check
from app.db import SessionLocal
from app.models import Assessment, Company, GuardrailEvent, Theme
from app.settings import settings

TOKEN_BUDGET = 800_000  # stop the run if it uses more than this


def log(session, company, theme, rule, detail):
    session.add(GuardrailEvent(company_id=company.id, theme_id=theme.id,
                               rule=rule, detail=(detail or "")[:500]))


def main(only_company=None):
    stored = rejected = skipped = tokens = 0
    with SessionLocal() as session:
        companies = session.scalars(select(Company).order_by(Company.name)).all()
        themes = session.scalars(select(Theme).order_by(Theme.code)).all()

        for company in companies:
            if only_company and company.name != only_company:
                continue
            for theme in themes:
                already = session.scalar(select(Assessment.id).where(
                    Assessment.company_id == company.id,
                    Assessment.theme_id == theme.id,
                    Assessment.prompt_version == PROMPT_VERSION,
                    Assessment.model == settings.llm_model,
                ))
                if already:
                    skipped += 1
                    continue
                if tokens > TOKEN_BUDGET:
                    print("Token budget reached, stopping.")
                    break

                result = assess(session, company, theme)
                tokens += result["tokens_in"] + result["tokens_out"]
                for error in result.get("rejections", []):
                    log(session, company, theme, "schema_retry", error)

                out = result["output"]
                if out is None:
                    log(session, company, theme, "schema", result["error"])
                    status = "REJECTED  schema"
                    rejected += 1
                else:
                    failures, warnings = check(out, result["passages"])
                    for rule, detail in failures + warnings:
                        log(session, company, theme, rule, detail)
                    if failures:
                        status = "REJECTED  " + ", ".join(sorted({rule for rule, _ in failures}))
                        rejected += 1
                    else:
                        pages = {p["chunk_id"]: p["page"] for p in result["passages"]}
                        session.add(Assessment(
                            company_id=company.id, theme_id=theme.id, score=out.score,
                            revenue_share_pct=out.revenue_share_pct, rationale=out.rationale,
                            citations=[{"chunk_id": c.chunk_id, "page": pages[c.chunk_id],
                                        "quote": c.quote} for c in out.citations],
                            insufficient_evidence=out.insufficient_evidence,
                            confidence=out.confidence, model=settings.llm_model,
                            prompt_version=PROMPT_VERSION,
                        ))
                        status = f"stored    score {out.score}"
                        stored += 1
                session.commit()
                print(f"{company.name:30} {theme.code:17} {status}")

    print(f"\nDone: {stored} stored, {rejected} rejected, {skipped} skipped, {tokens} tokens")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)