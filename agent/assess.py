import sys
from pathlib import Path

import anthropic
from pydantic import ValidationError
from sqlalchemy import select

from agent.retrieve import retrieve
from agent.schema import ASSESSMENT_TOOL, AssessmentOutput
from app.db import SessionLocal
from app.models import Company, Theme
from app.settings import settings

PROMPT_VERSION = "v2"
SYSTEM_PROMPT = (Path(__file__).parent / "prompts" / f"{PROMPT_VERSION}.md").read_text(encoding="utf-8")
client = anthropic.Anthropic(api_key=settings.llm_api_key)


def build_message(company, theme, passages):
    blocks = "\n\n".join(
        f'<passage id="{p["chunk_id"]}" page="{p["page"]}">\n{p["text"]}\n</passage>'
        for p in passages
    )
    return (
        f"Company: {company.name}\n\n"
        f"Theme: {theme.name}\nDefinition: {theme.definition}\n\n"
        f"Passages from the company's report:\n\n{blocks}\n\n"
        "Assess the company's exposure to this theme and call record_assessment."
    )


def assess(session, company, theme):
    """Retrieve evidence, ask the model, validate the answer. Retries once if invalid."""
    passages = retrieve(session, company.id, theme)
    base = build_message(company, theme, passages)
    result = {"output": None, "passages": passages, "tokens_in": 0, "tokens_out": 0, "error": None}

    text = base
    for attempt in range(2):
        response = client.messages.create(
            model=settings.llm_model,
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            tools=[ASSESSMENT_TOOL],
            messages=[{"role": "user", "content": text}],
        )
        result["tokens_in"] += response.usage.input_tokens
        result["tokens_out"] += response.usage.output_tokens

        answer = next((b.input for b in response.content if b.type == "tool_use"), None)
        if answer is None:
            result["error"] = "model did not call record_assessment"
        else:
            try:
                result["output"] = AssessmentOutput(**answer)
                result["error"] = None
                return result
            except ValidationError as e:
                result["error"] = str(e)
        result.setdefault("rejections", []).append(result["error"])
        text = f"{base}\n\nYour previous answer was rejected: {result['error']}\nTry again."
    return result


def main(company_name, theme_code):
    with SessionLocal() as session:
        company = session.scalar(select(Company).where(Company.name == company_name))
        theme = session.scalar(select(Theme).where(Theme.code == theme_code))
        if company is None or theme is None:
            print("Unknown company or theme code")
            return
        result = assess(session, company, theme)

    print(f"{company.name} / {theme.name}  (model {settings.llm_model}, prompt {PROMPT_VERSION})")
    print(f"Tokens in/out: {result['tokens_in']} / {result['tokens_out']}\n")
    out = result["output"]
    if out is None:
        print("REJECTED:", result["error"])
        return
    pages = {p["chunk_id"]: p["page"] for p in result["passages"]}
    print(f"Score: {out.score}   Revenue share: {out.revenue_share_pct}   "
          f"Confidence: {out.confidence}   Insufficient evidence: {out.insufficient_evidence}")
    print(f"\nRationale: {out.rationale}\n")
    for c in out.citations:
        print(f"  [passage {c.chunk_id}, page {pages.get(c.chunk_id, '?')}] \"{c.quote}\"")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
