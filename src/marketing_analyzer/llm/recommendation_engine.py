"""Provider-independent recommendation orchestration and validation."""

from pydantic import TypeAdapter, ValidationError

from .models import Recommendation
from .errors import RecommendationErrorCategory


class RecommendationValidationError(ValueError):
    """Raised when an LLM response is not a grounded recommendation list."""

    category = RecommendationErrorCategory.SCHEMA_VALIDATION_ERROR


def _safe_validation_summary(exc: ValidationError) -> str:
    """Return field/type diagnostics without echoing model output values.

    Pydantic's default error string includes the rejected input in some cases.
    Reports should retain enough information to debug prompt/model compatibility,
    but must not persist the provider response or any sensitive content.
    """
    locations: list[str] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ())) or "<root>"
        error_type = str(error.get("type", "validation_error"))
        locations.append(f"{location} ({error_type})")
    detail = "; ".join(locations[:20])
    if len(locations) > 20:
        detail += f"; and {len(locations) - 20} more"
    return "LLM recommendations failed schema validation" + (f": {detail}" if detail else ".")


def prioritize_findings(findings: list[dict]) -> list[dict]:
    return sorted(findings, key=lambda item: (-int(item.get("priority_score", 0)), item.get("finding_id", "")))


def build_context(report: dict) -> dict:
    return {
        "ads_summary": report["ads"].get("summary", {}),
        "seo_summary": report["seo"].get("summary", {}),
        "findings": prioritize_findings(report.get("insights", [])),
        "data_quality": report.get("data_quality", {}),
    }


def validate_recommendations(value: object, finding_ids: set[str]) -> list[dict]:
    try:
        recommendations = TypeAdapter(list[Recommendation]).validate_python(value)
    except ValidationError as exc:
        raise RecommendationValidationError(_safe_validation_summary(exc)) from exc
    for recommendation in recommendations:
        unknown = set(recommendation.related_finding_ids) - finding_ids
        if unknown:
            error = RecommendationValidationError(
                f"Recommendation {recommendation.recommendation_id} references unknown finding IDs: {sorted(unknown)}"
            )
            error.category = RecommendationErrorCategory.INVALID_FINDING_REFERENCE
            raise error
    return [recommendation.model_dump(mode="json") for recommendation in recommendations]


def build_action_plan(recommendations: list[dict]) -> dict:
    """Order validated recommendations without inventing deadlines."""
    immediate, short_term, longer_term = [], [], []
    for item in recommendations:
        priority = item.get("priority", "Low")
        effort = str(item.get("implementation_effort", "")).lower()
        if priority in {"Critical", "High"} and "high" not in effort:
            immediate.append(item)
        elif "high" in effort or priority == "Low":
            longer_term.append(item)
        else:
            short_term.append(item)

    priority_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    effort_order = {"low": 0, "medium": 1, "high": 2}

    def ordering_key(item: dict) -> tuple[int, int, str]:
        effort = str(item.get("implementation_effort", "")).lower()
        return (
            priority_order.get(str(item.get("priority", "Low")), 3),
            effort_order.get(effort, 3),
            str(item.get("recommendation_id", "")),
        )

    immediate.sort(key=ordering_key)
    short_term.sort(key=ordering_key)
    longer_term.sort(key=ordering_key)
    return {
        "immediate_actions": immediate,
        "short_term_optimisation": short_term,
        "longer_term_opportunities": longer_term,
        "ordering_reason": "Higher priority and lower stated implementation effort are ordered first; no deadlines are inferred.",
    }

