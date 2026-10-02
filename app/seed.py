"""Load companies, themes and a mock portfolio. Safe to run more than once."""
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.db import SessionLocal
from app.models import Company, Holding, Theme

COMPANIES = [
    # clear theme exposure
    ("Vestas Wind Systems", "Industrials", "DK"),
    ("Orsted", "Utilities", "DK"),
    ("Xylem", "Industrials", "US"),
    ("Veolia Environnement", "Utilities", "FR"),
    ("Novo Nordisk", "Health Care", "DK"),
    ("Roche", "Health Care", "CH"),
    ("Novonesis", "Materials", "DK"),
    ("Schneider Electric", "Industrials", "FR"),
    # ambiguous
    ("Siemens", "Industrials", "DE"),
    ("ABB", "Industrials", "CH"),
    ("Nestle", "Consumer Staples", "CH"),
    ("Danone", "Consumer Staples", "FR"),
    ("Geberit", "Industrials", "CH"),
    ("Unilever", "Consumer Staples", "GB"),
    # little or no exposure
    ("Shell", "Energy", "GB"),
    ("ExxonMobil", "Energy", "US"),
    ("LVMH", "Consumer Discretionary", "FR"),
    ("Philip Morris International", "Consumer Staples", "US"),
    ("Richemont", "Consumer Discretionary", "CH"),
    ("Ryanair", "Industrials", "IE"),
]

THEMES = [
    ("CLEAN_ENERGY", "Clean energy",
     "Products and services that generate renewable energy, store it, or make energy use "
     "substantially more efficient, such as wind, solar, grid technology and electrification."),
    ("WATER", "Water",
     "Products and services that supply, treat, distribute or save water, including water "
     "utilities, treatment technology, pumps, metering and efficient water use."),
    ("HEALTH", "Health",
     "Products and services that prevent, diagnose or treat disease, or improve access to "
     "health care, such as medicines, diagnostics and medical devices."),
    ("SUSTAINABLE_FOOD", "Sustainable food",
     "Products and services that make food production or consumption less resource-intensive "
     "or more nutritious, such as biological crop solutions, reduced food waste and healthier products."),
]

PORTFOLIO = "IMPACT-DEMO"
AS_OF = date(2026, 9, 30)
WEIGHTS = {  # percent of portfolio; must sum to 100
    "Vestas Wind Systems": 8, "Orsted": 7, "Xylem": 8, "Veolia Environnement": 7,
    "Novo Nordisk": 8, "Roche": 7, "Novonesis": 6, "Schneider Electric": 7,
    "Siemens": 5, "ABB": 5, "Nestle": 5, "Danone": 5, "Geberit": 4, "Unilever": 4,
    "Shell": 3, "ExxonMobil": 2, "LVMH": 3, "Philip Morris International": 2,
    "Richemont": 2, "Ryanair": 2,
}


def main() -> None:
    assert sum(WEIGHTS.values()) == 100, "Portfolio weights must sum to 100"

    with SessionLocal() as session:
        session.execute(
            insert(Company)
            .values([{"name": n, "sector": s, "country": c} for n, s, c in COMPANIES])
            .on_conflict_do_nothing(index_elements=["name"])
        )
        session.execute(
            insert(Theme)
            .values([{"code": c, "name": n, "definition": d} for c, n, d in THEMES])
            .on_conflict_do_nothing(index_elements=["code"])
        )
        company_ids = dict(session.execute(select(Company.name, Company.id)).all())
        session.execute(
            insert(Holding)
            .values([
                {"portfolio": PORTFOLIO, "company_id": company_ids[name],
                 "weight": weight, "as_of": AS_OF}
                for name, weight in WEIGHTS.items()
            ])
            .on_conflict_do_nothing(index_elements=["portfolio", "company_id", "as_of"])
        )
        session.commit()

        companies = session.scalar(select(func.count()).select_from(Company))
        themes = session.scalar(select(func.count()).select_from(Theme))
        total = session.scalar(select(func.sum(Holding.weight)).where(Holding.portfolio == PORTFOLIO))
        print(f"Companies: {companies}, themes: {themes}, portfolio weight total: {total}%")


if __name__ == "__main__":
    main()
