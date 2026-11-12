"""Numerically safe KPI calculations."""

import numpy as np
import pandas as pd


def safe_ratio(numerator: pd.Series, denominator: pd.Series, multiplier: float = 1.0) -> pd.Series:
    """Return a ratio with zero denominators represented as NaN, never as performance zero."""

    denominator = denominator.replace(0, np.nan)
    return numerator.div(denominator) * multiplier


def add_ad_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["ctr_pct"] = safe_ratio(result["clicks"], result["impressions"], 100)
    result["cpc_usd"] = safe_ratio(result["spend_usd"], result["clicks"])
    result["cpa_usd"] = safe_ratio(result["spend_usd"], result["purchases"])
    result["roas"] = safe_ratio(result["revenue_usd"], result["spend_usd"])
    result["conversion_rate_pct"] = safe_ratio(result["purchases"], result["clicks"], 100)
    result["cpm_usd"] = safe_ratio(result["spend_usd"], result["impressions"], 1000)
    result["frequency"] = safe_ratio(result["impressions"], result["reach"])
    return result


def add_seo_metrics(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    result["organic_ctr_pct"] = safe_ratio(result["clicks_28d"], result["impressions_28d"], 100)
    return result

