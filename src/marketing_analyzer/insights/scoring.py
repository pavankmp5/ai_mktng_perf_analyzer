"""Transparent, configurable business-impact prioritisation."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class ScoringWeights:
    potential_business_impact: float = 35
    financial_exposure_or_opportunity: float = 25
    reach_or_visibility: float = 20
    actionability: float = 10
    evidence_confidence: float = 10

    def __post_init__(self) -> None:
        total = sum((self.potential_business_impact, self.financial_exposure_or_opportunity, self.reach_or_visibility, self.actionability, self.evidence_confidence))
        if abs(total - 100) > 0.001 or any(value < 0 for value in (self.potential_business_impact, self.financial_exposure_or_opportunity, self.reach_or_visibility, self.actionability, self.evidence_confidence)):
            raise ValueError("Finding scoring weights must be non-negative and sum to 100")

    @classmethod
    def from_environment(cls) -> "ScoringWeights":
        names = {
            "potential_business_impact": "SCORING_WEIGHT_IMPACT",
            "financial_exposure_or_opportunity": "SCORING_WEIGHT_FINANCIAL",
            "reach_or_visibility": "SCORING_WEIGHT_REACH",
            "actionability": "SCORING_WEIGHT_ACTIONABILITY",
            "evidence_confidence": "SCORING_WEIGHT_EVIDENCE",
        }
        values = {field: float(os.getenv(env, default)) for field, env in names.items() for default in [getattr(cls(), field)]}
        return cls(**values)


def score_factors(factors: dict[str, float | None], weights: ScoringWeights | None = None) -> float:
    """Compute a 0–100 weighted score, renormalising only across available factors."""

    weights = weights or ScoringWeights()
    weight_map = {
        "potential_business_impact": weights.potential_business_impact,
        "financial_exposure_or_opportunity": weights.financial_exposure_or_opportunity,
        "reach_or_visibility": weights.reach_or_visibility,
        "actionability": weights.actionability,
        "evidence_confidence": weights.evidence_confidence,
    }
    available = [(weight_map[name], max(0.0, min(100.0, value))) for name, value in factors.items() if value is not None and name in weight_map]
    if not available:
        return 0.0
    score = sum(weight * value for weight, value in available) / sum(weight for weight, _ in available)
    return round(max(0.0, min(100.0, score)), 2)


def priority_for_score(score: float) -> str:
    if score >= 80:
        return "Critical"
    if score >= 60:
        return "High"
    if score >= 35:
        return "Medium"
    return "Low"


def percentile_score(value: float | None, series: list[float], higher_is_worse: bool = True) -> float | None:
    if value is None or not series:
        return None
    ordered = sorted(series)
    rank = sum(item <= value for item in ordered) / len(ordered) * 100
    return round(rank if higher_is_worse else 100 - rank, 2)

