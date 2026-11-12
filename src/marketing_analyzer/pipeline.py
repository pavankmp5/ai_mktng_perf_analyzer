"""Application orchestration."""

from datetime import datetime, timezone
import json
import os
from pathlib import Path

from .analysis.ads_analyzer import analyze_ads
from .analysis.seo_analyzer import analyze_seo
from .data_sources.csv_source import CsvDataSource
from .data_sources.source_metadata import ADS_METADATA, SEO_METADATA
from .data_processing.fingerprint import change_status, fingerprint_file
from .insights.rules import build_insights
from .llm.endpoints import EndpointRegistry, create_provider
from .llm.openrouter_provider import OpenRouterAuthenticationError, OpenRouterConfigurationError
from .llm.openrouter_provider import OpenRouterResponseError
from .llm.recommendation_engine import RecommendationValidationError, build_action_plan, build_context, validate_recommendations
from .llm.prompts import PROMPT_VERSION
from .llm.review import apply_review_decisions
from .reporting.report_writer import write_reports


def run_analysis(
    ads_path: Path,
    seo_path: Path,
    reports_dir: Path,
    recommendations: bool = False,
    llm_provider: str | None = None,
    llm_endpoint: str | None = None,
    llm_model: str | None = None,
) -> dict:
    ads_source = CsvDataSource(ADS_METADATA)
    seo_source = CsvDataSource(SEO_METADATA)
    ads_start = fingerprint_file(ads_path, 0, 0)
    seo_start = fingerprint_file(seo_path, 0, 0)
    ads = ads_source.read(ads_path)
    seo = seo_source.read(seo_path)
    previous_report = _read_previous_report(reports_dir / "marketing_report.json")
    ads_fingerprint = fingerprint_file(ads_path, len(ads), len(ADS_METADATA.required_columns))
    seo_fingerprint = fingerprint_file(seo_path, len(seo), len(SEO_METADATA.required_columns))
    if ads_start["sha256"] != ads_fingerprint["sha256"] or seo_start["sha256"] != seo_fingerprint["sha256"]:
        raise RuntimeError("An input CSV changed while it was being analysed; no report was written.")
    profile_name = llm_endpoint or os.getenv("LLM_ENDPOINT_PROFILE", "openrouter_default")
    default_models = {
        "openrouter_default": os.getenv("OPENROUTER_MODEL", "openrouter/auto"),
        "openai_direct": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "gemini_direct": os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "custom_openai_compatible": os.getenv("CUSTOM_LLM_MODEL", ""),
    }
    report = {
        "schema_version": "1.2",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_limitations": [
            "Inputs are current aggregates; no historical trend claims are made.",
            "AI recommendations are optional and remain separate from deterministic calculations.",
        ],
        "recommendations": [],
        "recommendations_status": "disabled" if not recommendations else "pending",
        "recommendations_error": None,
        "recommendations_error_category": None,
        "llm_provider": llm_provider or os.getenv("LLM_PROVIDER", {"openrouter_default": "openrouter", "openai_direct": "openai", "gemini_direct": "gemini", "custom_openai_compatible": "custom"}.get(profile_name, "openrouter")),
        "llm_endpoint_profile": profile_name,
        "llm_model": llm_model or default_models.get(profile_name, ""),
        "prompt_version": PROMPT_VERSION,
        "review_file": str(reports_dir / "recommendation_reviews.json"),
        "provenance": {"ads": ads_fingerprint, "seo": seo_fingerprint},
        "change_detection": {
            "ads": change_status((previous_report or {}).get("provenance"), ads_fingerprint, "ads"),
            "seo": change_status((previous_report or {}).get("provenance"), seo_fingerprint, "seo"),
            "both_changed": False,
            "any_changed": False,
        },
        "data_quality": {
            "ads": ads_source.last_quality_report,
            "seo": seo_source.last_quality_report,
        },
        "ads": analyze_ads(ads),
        "seo": analyze_seo(seo),
        "insights": build_insights(ads, seo),
        "action_plan": {"immediate_actions": [], "short_term_optimisation": [], "longer_term_opportunities": [], "ordering_reason": "No AI recommendations were generated."},
    }
    report["executive_summary"] = _executive_summary(report)
    if recommendations:
        try:
            registry = EndpointRegistry()
            profile = registry.get(profile_name)
            if llm_provider and llm_provider != profile.provider:
                raise ValueError(
                    f"LLM_PROVIDER '{llm_provider}' conflicts with endpoint profile "
                    f"'{profile.name}' provider '{profile.provider}'"
                )
            provider = create_provider(profile, model=llm_model)
            raw_recommendations = provider.generate_recommendations(build_context(report))
            finding_ids = {item["finding_id"] for item in report["insights"]}
            report["recommendations"] = apply_review_decisions(validate_recommendations(raw_recommendations, finding_ids), reports_dir / "recommendation_reviews.json")
            report["recommendations_status"] = "generated"
            report["action_plan"] = build_action_plan(report["recommendations"])
        except OpenRouterConfigurationError:
            report["recommendations_status"] = "skipped_due_to_configuration"
            report["recommendations_error"] = "Required LLM credentials are not configured."
        except OpenRouterAuthenticationError as exc:
            report["recommendations_status"] = "failed"
            report["recommendations_error"] = str(exc)
            report["recommendations_error_category"] = exc.category
        except RecommendationValidationError as exc:
            report["recommendations_status"] = "failed"
            report["recommendations_error"] = str(exc)
            report["recommendations_error_category"] = RecommendationValidationError.category
        except OpenRouterResponseError as exc:
            report["recommendations_status"] = "failed"
            report["recommendations_error"] = str(exc)
            report["recommendations_error_category"] = exc.category
        except (ValueError, TypeError):
            report["recommendations_status"] = "skipped_due_to_configuration"
            report["recommendations_error"] = "LLM provider or endpoint configuration is invalid."
        except Exception:
            report["recommendations_status"] = "failed"
            report["recommendations_error"] = "The LLM provider failed; deterministic analysis was preserved."
            report["recommendations_error_category"] = "provider_error"
    report["change_detection"]["both_changed"] = report["change_detection"]["ads"]["changed"] and report["change_detection"]["seo"]["changed"]
    report["change_detection"]["any_changed"] = report["change_detection"]["ads"]["changed"] or report["change_detection"]["seo"]["changed"]
    write_reports(report, reports_dir)
    return report


def _executive_summary(report: dict) -> dict:
    findings = sorted(report["insights"], key=lambda item: (-item["priority_score"], item["finding_id"]))
    return {
        "headline": f"{len(findings)} current performance findings identified across advertising and SEO.",
        "advertising": report["ads"]["summary"],
        "seo": report["seo"]["summary"],
        "data_quality": report["data_quality"],
        "highest_priority_findings": findings[:5],
        "highest_value_opportunities": [item for item in findings if item["type"] == "opportunity"][:5],
        "priority_score_explanation": "Priority is a reproducible weighted score: impact 35%, financial exposure/opportunity 25%, reach/visibility 20%, actionability 10%, evidence confidence 10%; missing factors are excluded and remaining weights renormalised.",
    }


def _read_previous_report(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) and "provenance" in value else None
    except (OSError, json.JSONDecodeError, TypeError):
        return None

