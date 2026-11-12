import numpy as np
import pandas as pd

from marketing_analyzer.data_processing.metrics import add_ad_metrics


def test_ad_metrics_use_nan_for_zero_denominators() -> None:
    frame = pd.DataFrame({
        "spend_usd": [100.0, 0.0],
        "clicks": [0, 1],
        "purchases": [0, 0],
        "revenue_usd": [0.0, 0.0],
        "impressions": [0, 100],
        "reach": [0, 50],
    })
    result = add_ad_metrics(frame)
    assert np.isnan(result.loc[0, "ctr_pct"])
    assert np.isnan(result.loc[0, "cpc_usd"])
    assert result.loc[0, "roas"] == 0.0  # Revenue is observed and spend is available.
    assert np.isnan(result.loc[1, "roas"])  # ROAS is unavailable when spend is zero.

