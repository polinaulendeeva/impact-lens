import re
import unicodedata
from difflib import SequenceMatcher

INJECTION = re.compile(
    r"ignore (all |any )?(previous|prior|above) instructions|disregard (the|all) (above|previous)",
    re.IGNORECASE,
)


def normalise(text):
    """Make quote and passage comparable: same case, no layout differences."""
    text = unicodedata.normalize("NFKC", text).lower().replace("\u00ad", "")
    text = re.sub(r"(?<=[a-z])-\s+(?=[a-z])", "", text)   # "technol- ogies" -> "technologies"
    text = re.sub(r"[^a-z0-9%]+", " ", text)
    return " ".join(text.split())


def part_found(q, p):
    if q in p:
        return True
    match = SequenceMatcher(None, q, p, autojunk=False).find_longest_match(0, len(q), 0, len(p))
    return match.size >= 0.8 * len(q)


def quote_found(quote, passage_text):
    """Every fragment of the quote (split at '...') must appear in the passage."""
    p = normalise(passage_text)
    parts = [normalise(x) for x in re.split(r"\.{3,}|…", quote)]
    parts = [x for x in parts if x]
    return bool(parts) and all(part_found(x, p) for x in parts)


def figure_found(value, texts):
    """Is this percentage actually written in one of the cited passages?"""
    pattern = re.compile(rf"(?<![\d.]){re.escape(f'{value:g}')}\s*(%|percent|per cent)")
    return any(pattern.search(unicodedata.normalize("NFKC", t).lower()) for t in texts)


def check(output, passages):
    """Return (failures, warnings). Any failure means the assessment is not stored."""
    by_id = {p["chunk_id"]: p for p in passages}
    failures, warnings = [], []

    valid = 0
    for c in output.citations:
        passage = by_id.get(c.chunk_id)
        if passage is None:
            failures.append(("citation_exists", f"passage {c.chunk_id} was not provided"))
        elif not quote_found(c.quote, passage["text"]):
            failures.append(("quote_matches", f"passage {c.chunk_id}: {c.quote[:80]}"))
        else:
            valid += 1

    if output.score > 0 and valid == 0:
        failures.append(("no_evidence_no_claim", f"score {output.score} with no valid citation"))

    if output.insufficient_evidence and output.score > 0:
        failures.append(("inconsistent", f"insufficient evidence but score {output.score}"))

    if output.revenue_share_pct is not None:
        cited = [by_id[c.chunk_id]["text"] for c in output.citations if c.chunk_id in by_id]
        if not figure_found(output.revenue_share_pct, cited):
            failures.append(("revenue_share_supported",
                             f"{output.revenue_share_pct:g}% is not stated in any cited passage"))

    for p in passages:
        if INJECTION.search(p["text"]):
            warnings.append(("injection_suspected", f"passage {p['chunk_id']}"))

    return failures, warnings