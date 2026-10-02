from typing import Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    chunk_id: int
    quote: str = Field(min_length=10, max_length=400)


class AssessmentOutput(BaseModel):
    score: int = Field(ge=0, le=3)
    revenue_share_pct: float | None = Field(default=None, ge=0, le=100)
    rationale: str = Field(min_length=20, max_length=1200)
    citations: list[Citation]
    insufficient_evidence: bool
    confidence: Literal["low", "medium", "high"]


# The same shape, described for the LLM as a tool it must call to submit its answer.
ASSESSMENT_TOOL = {
    "name": "record_assessment",
    "description": "Record the assessment of one company against one impact theme.",
    "input_schema": {
        "type": "object",
        "properties": {
            "score": {
                "type": "integer",
                "enum": [0, 1, 2, 3],
                "description": "Exposure to the theme: 0 none, 1 minor, 2 material, 3 core business.",
            },
            "revenue_share_pct": {
                "type": ["number", "null"],
                "description": "Share of revenue tied to the theme, only if a passage states it. Otherwise null.",
            },
            "rationale": {
                "type": "string",
                "description": "Up to 120 words explaining the score, based only on the passages.",
            },
            "citations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "chunk_id": {"type": "integer", "description": "The id of the passage."},
                        "quote": {"type": "string", "description": "A short exact quote from that passage."},
                    },
                    "required": ["chunk_id", "quote"],
                },
            },
            "insufficient_evidence": {
                "type": "boolean",
                "description": "True if the passages do not support any score.",
            },
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
        },
        "required": ["score", "revenue_share_pct", "rationale", "citations",
                     "insufficient_evidence", "confidence"],
    },
}