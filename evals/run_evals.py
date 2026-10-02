import csv
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Assessment, Company, Theme
from app.settings import settings

GOLD = Path("evals/gold.csv")
OUT = Path("evals/results")


def pct(part, whole):
    return f"{100 * part / whole:.0f}%" if whole else "n/a"


def main(prompt_version="v1"):
    with open(GOLD, newline="", encoding="utf-8") as f:
        gold = list(csv.DictReader(f))

    rows = []
    with SessionLocal() as session:
        for g in gold:
            found = session.execute(
                select(Assessment.score, Assessment.confidence)
                .join(Company, Company.id == Assessment.company_id)
                .join(Theme, Theme.id == Assessment.theme_id)
                .where(Company.name == g["company"], Theme.code == g["theme"],
                       Assessment.prompt_version == prompt_version,
                       Assessment.model == settings.llm_model)
                .order_by(Assessment.created_at.desc())
                .limit(1)
            ).first()
            rows.append({
                "company": g["company"], "theme": g["theme"],
                "expected": int(g["expected_score"]),
                "model": found.score if found else None,
                "confidence": found.confidence if found else None,
            })

    answered = [r for r in rows if r["model"] is not None]
    rejected = [r for r in rows if r["model"] is None]
    exact = [r for r in answered if r["model"] == r["expected"]]
    within_one = [r for r in answered if abs(r["model"] - r["expected"]) <= 1]
    too_high = [r for r in answered if r["model"] > r["expected"]]
    too_low = [r for r in answered if r["model"] < r["expected"]]
    exposed = [r for r in answered if r["expected"] > 0]
    exposed_exact = [r for r in exposed if r["model"] == r["expected"]]
    bias = sum(r["model"] - r["expected"] for r in answered) / len(answered) if answered else 0

    out = [
        f"# Eval results: prompt {prompt_version}, model {settings.llm_model}",
        f"\nRun on {date.today()}. Gold set: {len(rows)} company and theme pairs.\n",
        "| Measure | Result |", "| --- | --- |",
        f"| Answered (passed guardrails) | {len(answered)} of {len(rows)} |",
        f"| Rejected by guardrails | {len(rejected)} |",
        f"| Exact match, of answered | {len(exact)} of {len(answered)} ({pct(len(exact), len(answered))}) |",
        f"| Exact match, counting rejections as wrong | {len(exact)} of {len(rows)} ({pct(len(exact), len(rows))}) |",
        f"| Within one point, of answered | {len(within_one)} of {len(answered)} ({pct(len(within_one), len(answered))}) |",
        f"| Exact match where I expected exposure (score above 0) | {len(exposed_exact)} of {len(exposed)} ({pct(len(exposed_exact), len(exposed))}) |",
        f"| Model scored higher than me | {len(too_high)} |",
        f"| Model scored lower than me | {len(too_low)} |",
        f"| Average difference (model minus me) | {bias:+.2f} |",
        "\n## Accuracy by the model's stated confidence\n",
        "| Confidence | Answers | Exact |", "| --- | --- | --- |",
    ]
    for level in ("high", "medium", "low"):
        group = [r for r in answered if r["confidence"] == level]
        hits = [r for r in group if r["model"] == r["expected"]]
        out.append(f"| {level} | {len(group)} | {len(hits)} ({pct(len(hits), len(group))}) |")

    out += ["\n## Disagreements\n", "| Company | Theme | Me | Model | Confidence |", "| --- | --- | --- | --- | --- |"]
    for r in answered:
        if r["model"] != r["expected"]:
            out.append(f"| {r['company']} | {r['theme']} | {r['expected']} | {r['model']} | {r['confidence']} |")

    out += ["\n## Rejected by guardrails (no stored answer)\n", "| Company | Theme | Me |", "| --- | --- | --- |"]
    for r in rejected:
        out.append(f"| {r['company']} | {r['theme']} | {r['expected']} |")

    report = "\n".join(out) + "\n"
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{prompt_version}_{date.today()}.md"
    path.write_text(report, encoding="utf-8")
    print(report)
    print(f"Saved to {path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "v1")
    