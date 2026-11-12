"""Advertising KPI and comparison analysis."""

import pandas as pd

from marketing_analyzer.data_processing.metrics import add_ad_metrics


def analyze_ads(frame: pd.DataFrame) -> dict:
    metrics = add_ad_metrics(frame)
    totals = metrics[["spend_usd", "clicks", "purchases", "revenue_usd", "impressions", "reach"]].sum()
    aggregate = add_ad_metrics(pd.DataFrame([totals])).iloc[0].to_dict()
    return {
        "row_count": len(metrics),
        "summary": _record(aggregate),
        "campaigns": _records(metrics),
        "by_platform": _group(metrics, "platform"),
        "by_campaign_type": _group(metrics, "campaign_type"),
    }


def _group(frame: pd.DataFrame, column: str) -> list[dict]:
    if frame.empty:
        return []
    grouped = frame.groupby(column, dropna=False).agg(
        spend_usd=("spend_usd", "sum"), clicks=("clicks", "sum"),
        purchases=("purchases", "sum"), revenue_usd=("revenue_usd", "sum"),
        impressions=("impressions", "sum"), reach=("reach", "sum"),
    ).reset_index()
    return _records(add_ad_metrics(grouped))


def _records(frame: pd.DataFrame) -> list[dict]:
    return [_record(record) for record in frame.to_dict(orient="records")]


def _record(record: dict) -> dict:
    result = {}
    for key, value in record.items():
        if pd.isna(value):
            result[key] = None
        elif isinstance(value, float):
            result[key] = round(value, 4)
        else:
            result[key] = value.item() if hasattr(value, "item") else value
    return result

