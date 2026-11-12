"""Persistent human review decisions for generated recommendations."""

import json
import hashlib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReviewDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recommendation_id: str = Field(min_length=1)
    review_status: str = Field(pattern="^(pending_review|approved|rejected|needs_revision)$")
    reviewer_note: str = ""
    recommendation_fingerprint: str | None = None
    history: list[dict[str, Any]] = Field(default_factory=list)


def load_review_decisions(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return {item["recommendation_id"]: ReviewDecision.model_validate(item).model_dump() for item in raw}
    except (OSError, json.JSONDecodeError, TypeError, KeyError, ValueError):
        return {}


def save_review_decision(path: Path, decision: ReviewDecision) -> None:
    decisions = load_review_decisions(path)
    previous = decisions.get(decision.recommendation_id)
    if previous and previous.get("recommendation_fingerprint") != decision.recommendation_fingerprint:
        decision.history = previous.get("history", []) + [{key: previous.get(key) for key in ("recommendation_fingerprint", "review_status", "reviewer_note")}]
    decisions[decision.recommendation_id] = decision.model_dump()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(list(decisions.values()), indent=2), encoding="utf-8")


def apply_review_decisions(recommendations: list[dict], path: Path) -> list[dict]:
    decisions = load_review_decisions(path)
    result = []
    for recommendation in recommendations:
        item = dict(recommendation)
        fingerprint = recommendation_fingerprint(item)
        decision = decisions.get(item["recommendation_id"], {})
        applicable = decision.get("recommendation_fingerprint") == fingerprint
        item["review_status"] = decision.get("review_status", "pending_review") if applicable else "pending_review"
        item["reviewer_note"] = decision.get("reviewer_note", "") if applicable else ""
        item["review_fingerprint"] = fingerprint
        result.append(item)
    return result


def recommendation_fingerprint(recommendation: dict) -> str:
    content = {key: value for key, value in recommendation.items() if key not in {"review_status", "reviewer_note", "review_fingerprint"}}
    return hashlib.sha256(json.dumps(content, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()
