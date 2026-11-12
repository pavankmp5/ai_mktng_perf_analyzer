"""Deterministic, peer-relative marketing findings.

Thresholds are derived from the supplied rows (medians and quartiles), not
external benchmarks.  The source row number is retained in evidence.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd

from marketing_analyzer.data_processing.metrics import add_ad_metrics, add_seo_metrics

from .models import Finding
from .scoring import ScoringWeights, percentile_score, priority_for_score, score_factors


def build_insights(ads: pd.DataFrame, seo: pd.DataFrame) -> list[dict]:
    weights = ScoringWeights.from_environment()
    return _ads_findings(add_ad_metrics(ads), weights) + _seo_findings(add_seo_metrics(seo), weights)


def _ads_findings(df: pd.DataFrame, weights: ScoringWeights) -> list[dict]:
    findings: list[dict] = []
    numeric = {name: _values(df, name) for name in ("spend_usd", "roas", "cpa", "conversion_rate_pct", "ctr_pct", "cpc")}
    medians = {name: _median(values) for name, values in numeric.items()}
    for index, row in df.iterrows():
        entity = str(row.get("campaign", f"row-{index}"))
        source = _source_row(index)
        spend = _number(row.get("spend_usd")); revenue = _number(row.get("revenue_usd"))
        conversions = _number(row.get("purchases")); clicks = _number(row.get("clicks"))
        reach = _number(row.get("impressions"));

        def add(kind: str, suffix: str, title: str, description: str, metrics: dict[str, Any], evidence: str, action: str, factors: dict[str, float | None], limitations: list[str]) -> None:
            findings.append(_finding(f"ads-{index}-{suffix}", "Advertising", entity, kind, title, description, metrics, [f"{source}: {evidence}"], action, factors, limitations, weights))

        if spend is not None and numeric["spend_usd"] and spend >= _quantile(numeric["spend_usd"], .75):
            add("problem", "high-spend", f"High-spend campaign: {entity}", "Spend is in the upper quartile of the supplied campaigns.", {"spend_usd": spend}, f"spend_usd={spend}", "Review spend allocation alongside conversions, revenue and ROAS.", {"potential_business_impact": 75, "financial_exposure_or_opportunity": percentile_score(spend, numeric["spend_usd"]), "reach_or_visibility": 60, "actionability": 75, "evidence_confidence": 95}, ["Relative to this dataset only; no budget target is available."])
        roas = _number(row.get("roas"))
        if roas is not None and medians["roas"] is not None and roas < medians["roas"] and spend is not None and spend >= (medians["spend_usd"] or 0):
            add("problem", "low-roas", f"Below-peer ROAS: {entity}", "ROAS is below the campaign median while spend is at or above the median.", {"roas": roas, "spend_usd": spend}, f"roas={roas}; peer_median_roas={medians['roas']}", "Investigate creative, audience, placement and landing-page efficiency before changing budget.", {"potential_business_impact": 75, "financial_exposure_or_opportunity": 70, "reach_or_visibility": 55, "actionability": 70, "evidence_confidence": 90}, ["A lower relative ROAS is not proof of unprofitability without business margin targets."])
        if roas is not None and roas >= _quantile(numeric["roas"], .75):
            add("opportunity", "high-roas", f"High-ROAS opportunity: {entity}", "ROAS is in the upper quartile of the supplied campaigns.", {"roas": roas, "spend_usd": spend}, f"roas={roas}; upper_quartile={_quantile(numeric['roas'], .75)}", "Run a controlled review of whether learnings can be replicated; do not automatically increase budget.", {"potential_business_impact": 65, "financial_exposure_or_opportunity": 70, "reach_or_visibility": 45, "actionability": 65, "evidence_confidence": 90}, ["High ROAS alone does not establish incremental scalability or causal performance."])
        for metric, suffix, label, action in (("cpa", "high-cpa", "CPA", "Review conversion quality and acquisition costs."), ("cpc", "high-cpc", "CPC", "Review targeting, relevance and auction efficiency.")):
            value = _number(row.get(metric))
            if value is not None and numeric[metric] and value >= _quantile(numeric[metric], .75):
                add("problem", suffix, f"High {label}: {entity}", f"{label} is in the upper quartile of supplied campaigns.", {metric: value}, f"{metric}={value}; upper_quartile={_quantile(numeric[metric], .75)}", action, {"potential_business_impact": 60, "financial_exposure_or_opportunity": 65, "reach_or_visibility": 50, "actionability": 75, "evidence_confidence": 85}, ["Relative comparison only; no external efficiency benchmark is used."])
        for metric, suffix, label in (("conversion_rate_pct", "low-conversion", "conversion rate"), ("ctr_pct", "low-ctr", "CTR")):
            value = _number(row.get(metric))
            if value is not None and medians[metric] is not None and value < medians[metric]:
                add("problem", suffix, f"Below-peer {label}: {entity}", f"{label.capitalize()} is below the campaign median.", {metric: value}, f"{metric}={value}; peer_median={medians[metric]}", "Compare this campaign with stronger peers and test the most relevant creative or audience variable.", {"potential_business_impact": 55, "financial_exposure_or_opportunity": 55, "reach_or_visibility": 55, "actionability": 75, "evidence_confidence": 85}, ["A relative result is not an absolute failure without campaign objectives."])
        numeric_revenue = _values(df, "revenue_usd")
        if revenue is not None and numeric_revenue:
            if revenue >= _quantile(numeric_revenue, .75) and conversions is not None:
                add("opportunity", "meaningful-revenue", f"Meaningful revenue contribution: {entity}", "Revenue is in the upper quartile of supplied campaigns.", {"revenue_usd": revenue, "purchases": conversions}, f"revenue_usd={revenue}; upper_quartile={_quantile(numeric_revenue, .75)}", "Protect the campaign's measured revenue contribution while checking incrementality and conversion quality.", {"potential_business_impact": 65, "financial_exposure_or_opportunity": 75, "reach_or_visibility": 55, "actionability": 60, "evidence_confidence": 90}, ["Revenue contribution is observed; incrementality and margin are unavailable."])
    return findings


def _seo_findings(df: pd.DataFrame, weights: ScoringWeights) -> list[dict]:
    findings: list[dict] = []
    impressions = _values(df, "impressions_28d"); ctr = _values(df, "organic_ctr_pct"); position = _values(df, "avg_position"); load = _values(df, "page_load_ms")
    median_ctr = _median(ctr); median_impressions = _median(impressions)
    for index, row in df.iterrows():
        entity = str(row.get("url_slug", row.get("product_id", f"row-{index}"))); source = _source_row(index)
        def add(kind: str, suffix: str, title: str, description: str, metrics: dict[str, Any], evidence: str, action: str, factors: dict[str, float | None], limitations: list[str]) -> None:
            findings.append(_finding(f"seo-{index}-{suffix}", "SEO", entity, kind, title, description, metrics, [f"{source}: {evidence}"], action, factors, limitations, weights))
        imp = _number(row.get("impressions_28d")); value_ctr = _number(row.get("organic_ctr_pct")); pos = _number(row.get("avg_position")); load_ms = _number(row.get("page_load_ms")); indexed = _bool(row.get("indexed"))
        if imp is not None and value_ctr is not None and median_ctr is not None and median_impressions is not None and imp >= median_impressions and value_ctr < median_ctr:
            add("opportunity", "high-impression-low-ctr", f"High-impression, below-peer CTR page: {entity}", "The page has at least median impressions but below-median organic CTR.", {"impressions_28d": imp, "organic_ctr_pct": value_ctr}, f"impressions_28d={imp}; organic_ctr_pct={value_ctr}; peer_median_ctr={median_ctr}", "Review title, snippet and search-intent alignment while considering average position.", {"potential_business_impact": 65, "financial_exposure_or_opportunity": 35, "reach_or_visibility": 80, "actionability": 75, "evidence_confidence": 90}, ["CTR varies with query mix and position; 28-day aggregate data has no history."])
        if indexed is False:
            add("problem", "not-indexed", f"Non-indexed page: {entity}", "The page is marked as not indexed.", {"indexed": False}, "indexed=False", "Inspect indexability, canonicalisation, robots directives and sitemap coverage.", {"potential_business_impact": 70, "financial_exposure_or_opportunity": 20, "reach_or_visibility": 85, "actionability": 85, "evidence_confidence": 95}, ["The dataset does not explain why the page is not indexed."])
        if pos is not None and position and pos >= _quantile(position, .75):
            add("opportunity", "weak-visibility", f"Weaker search visibility: {entity}", "Average position is in the weaker quartile of supplied pages.", {"avg_position": pos}, f"avg_position={pos}; upper_quartile={_quantile(position, .75)}", "Review page relevance, internal links and content coverage for the queries represented.", {"potential_business_impact": 55, "financial_exposure_or_opportunity": 20, "reach_or_visibility": 80, "actionability": 65, "evidence_confidence": 85}, ["Average position is a 28-day aggregate and is not a historical trend."])
        if load_ms is not None and load and load_ms >= _quantile(load, .75):
            add("problem", "slow-load", f"Comparatively slow page load: {entity}", "Page load time is in the upper quartile of supplied pages.", {"page_load_ms": load_ms}, f"page_load_ms={load_ms}; upper_quartile={_quantile(load, .75)}", "Profile the page and prioritise the largest measurable loading bottlenecks.", {"potential_business_impact": 45, "financial_exposure_or_opportunity": 15, "reach_or_visibility": 65, "actionability": 75, "evidence_confidence": 85}, ["No device, geography or lab/field measurement context is supplied."])
        if pos is not None and value_ctr is not None and position and median_ctr is not None and pos <= _quantile(position, .25) and value_ctr >= median_ctr:
            add("opportunity", "strong-visibility", f"Strong organic visibility: {entity}", "The page combines stronger relative position with at least median CTR.", {"avg_position": pos, "organic_ctr_pct": value_ctr}, f"avg_position={pos}; organic_ctr_pct={value_ctr}", "Document the page's content and internal-linking patterns for controlled reuse.", {"potential_business_impact": 45, "financial_exposure_or_opportunity": 15, "reach_or_visibility": 75, "actionability": 55, "evidence_confidence": 85}, ["This is a current relative signal, not evidence of future or historical change."])
    return findings


def _finding(finding_id: str, dataset: str, entity: str, kind: str, title: str, description: str, metrics: dict[str, Any], evidence: list[str], action: str, factors: dict[str, float | None], limitations: list[str], weights: ScoringWeights) -> dict:
    score = score_factors(factors, weights); priority = priority_for_score(score)
    finding = Finding(finding_id=finding_id, category=kind, source_dataset=dataset, entity_name=entity, title=title, description=description, severity=priority, impact_score=round(factors.get("potential_business_impact") or 0, 2), priority_score=score, supporting_metrics=metrics, evidence=evidence, business_interpretation=description, limitations=limitations, recommended_action=action, dataset=dataset.lower(), type=kind, priority=priority, priority_factors=factors)
    return finding.to_report_dict()


def _number(value: Any) -> float | None:
    try:
        return None if pd.isna(value) else float(value)
    except (TypeError, ValueError):
        return None


def _bool(value: Any) -> bool | None:
    if pd.isna(value): return None
    if isinstance(value, bool): return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _values(df: pd.DataFrame, column: str) -> list[float]:
    if column not in df: return []
    return [value for value in (_number(item) for item in df[column]) if value is not None and math.isfinite(value)]


def _median(values: list[float]) -> float | None:
    return float(pd.Series(values).median()) if values else None


def _quantile(values: list[float], quantile: float) -> float:
    return float(pd.Series(values).quantile(quantile)) if values else 0.0


def _source_row(index: Any) -> str:
    return f"source row {int(index) + 2}" if isinstance(index, (int, float)) else f"source index {index}"
