"""Command-line entry point."""

import argparse
import json
import logging
import os
from pathlib import Path

from .config.settings import load_settings
from .pipeline import run_analysis
from .llm.review import ReviewDecision, recommendation_fingerprint, save_review_decision


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyse advertising and SEO marketing performance.")
    parser.add_argument("--ads", type=Path, help="Path to ads_data.csv")
    parser.add_argument("--seo", type=Path, help="Path to seo_data.csv")
    parser.add_argument("--reports-dir", type=Path, help="Output directory for JSON and HTML reports")
    recommendation_group = parser.add_mutually_exclusive_group()
    recommendation_group.add_argument("--recommendations", action="store_true", help="Opt in to LLM recommendation generation")
    recommendation_group.add_argument("--no-recommendations", action="store_true", help="Force deterministic-only execution")
    parser.add_argument("--llm-provider", help="LLM provider adapter name")
    parser.add_argument("--llm-endpoint", help="Named LLM endpoint profile")
    parser.add_argument("--llm-model", help="Provider/model identifier")
    parser.add_argument("--inspect-recommendations", action="store_true", help="Print recommendations from the existing JSON report")
    parser.add_argument("--review-rec", help="Recommendation ID to review without an LLM call")
    parser.add_argument("--review-status", choices=["pending_review", "approved", "rejected", "needs_revision"])
    parser.add_argument("--review-note", default="", help="Optional human review note")
    parser.add_argument("--review-file", type=Path, help="Review decision JSON file")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    settings = load_settings()
    review_file = args.review_file or settings.reports_dir / "recommendation_reviews.json"
    if args.review_rec:
        if not args.review_status:
            raise SystemExit("--review-status is required with --review-rec")
        report_path = settings.reports_dir / "marketing_report.json"
        if not report_path.exists():
            raise SystemExit(f"Report not found: {report_path}")
        report = json.loads(report_path.read_text(encoding="utf-8"))
        recommendation = next((item for item in report.get("recommendations", []) if item.get("recommendation_id") == args.review_rec), None)
        if recommendation is None:
            raise SystemExit(f"Recommendation not found: {args.review_rec}")
        save_review_decision(review_file, ReviewDecision(recommendation_id=args.review_rec, review_status=args.review_status, reviewer_note=args.review_note, recommendation_fingerprint=recommendation_fingerprint(recommendation)))
        print(f"Saved review decision for {args.review_rec}: {args.review_status}")
        return
    if args.inspect_recommendations:
        report_path = settings.reports_dir / "marketing_report.json"
        raise SystemExit(_inspect_report(report_path))
    logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO), format="%(levelname)s %(message)s")
    report = run_analysis(
        args.ads or settings.ads_data_path,
        args.seo or settings.seo_data_path,
        args.reports_dir or settings.reports_dir,
        recommendations=False if args.no_recommendations else args.recommendations or os.getenv("ENABLE_AI_RECOMMENDATIONS", "false").lower() in {"1", "true", "yes", "on"},
        llm_provider=args.llm_provider,
        llm_endpoint=args.llm_endpoint,
        llm_model=args.llm_model,
    )
    print(f"Analysed {report['ads']['row_count']} advertising rows and {report['seo']['row_count']} SEO rows.")


def _inspect_report(report_path: Path) -> int:
    """Print safe report diagnostics and return a process exit code."""

    resolved = report_path.resolve()
    print(f"Report path: {resolved}")
    print(f"File exists: {resolved.exists()}")
    if not resolved.exists():
        print("Report not found.")
        print(f"Expected path: {resolved}")
        print("Check whether report generation completed successfully.")
        return 1
    try:
        report = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        print(f"Report unreadable: {type(exc).__name__}")
        return 1
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: line {exc.lineno}, column {exc.colno}")
        return 1
    if not isinstance(report, dict):
        print("Invalid JSON: report root must be an object.")
        return 1
    recommendations = report.get("recommendations", [])
    if not isinstance(recommendations, list):
        recommendations = []
    print(f"Status: {report.get('recommendations_status', 'unknown')}")
    print(f"Error: {report.get('recommendations_error_category')}")
    if report.get("recommendations_error"):
        print(f"Details: {report['recommendations_error']}")
    print(f"Recommendations: {len(recommendations)}")
    for item in recommendations:
        if isinstance(item, dict):
            print(f"{item.get('recommendation_id', '<missing-id>')} [{item.get('review_status', 'pending_review')}] {item.get('title', '<untitled>')}")
    return 0


if __name__ == "__main__":
    main()

