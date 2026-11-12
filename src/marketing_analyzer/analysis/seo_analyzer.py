"""SEO visibility and technical performance analysis."""

import pandas as pd

from marketing_analyzer.data_processing.metrics import add_seo_metrics


def analyze_seo(frame: pd.DataFrame) -> dict:
    metrics = add_seo_metrics(frame)
    indexed = metrics["indexed"].astype("boolean") if not metrics.empty else pd.Series(dtype="boolean")
    total_impressions = metrics["impressions_28d"].sum() if not metrics.empty else 0
    total_clicks = metrics["clicks_28d"].sum() if not metrics.empty else 0
    return {
        "row_count": len(metrics),
        "pages": _records(metrics),
        "summary": {
            "total_impressions_28d": int(total_impressions),
            "total_clicks_28d": int(total_clicks),
            "organic_ctr_pct": round(float(total_clicks / total_impressions * 100), 4) if total_impressions else None,
            "average_search_position": _mean(metrics, "avg_position"),
            "indexed_page_percentage": round(float(indexed.mean() * 100), 4) if len(indexed) else None,
            "non_indexed_page_count": int((~indexed.fillna(False)).sum()) if len(indexed) else 0,
            "average_page_load_ms": _mean(metrics, "page_load_ms"),
        },
        "by_category": _category_summary(metrics),
    }


def _mean(frame: pd.DataFrame, column: str) -> float | None:
    value = frame[column].mean() if not frame.empty else None
    return None if pd.isna(value) else round(float(value), 4)


def _category_summary(frame: pd.DataFrame) -> list[dict]:
    if frame.empty:
        return []
    summary = frame.groupby("category", dropna=False).agg(
        pages=("product_id", "count"), impressions_28d=("impressions_28d", "sum"),
        clicks_28d=("clicks_28d", "sum"), avg_position=("avg_position", "mean"),
        average_page_load_ms=("page_load_ms", "mean"),
    ).reset_index().pipe(add_seo_metrics)
    return _records(summary)


def _records(frame: pd.DataFrame) -> list[dict]:
    records = []
    for record in frame.to_dict(orient="records"):
        records.append({key: None if pd.isna(value) else round(value, 4) if isinstance(value, float) else value.item() if hasattr(value, "item") else value for key, value in record.items()})
    return records

