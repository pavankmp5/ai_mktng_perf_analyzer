from pathlib import Path

import pandas as pd
import pytest

from marketing_analyzer.analysis.ads_analyzer import analyze_ads
from marketing_analyzer.analysis.seo_analyzer import analyze_seo
from marketing_analyzer.data_sources.csv_source import CsvDataSource, DataValidationError
from marketing_analyzer.data_sources.source_metadata import ADS_METADATA, SEO_METADATA


PROJECT_ROOT = Path(__file__).parents[1]


def test_real_ads_and_seo_files_load_with_expected_quality() -> None:
    ads_source = CsvDataSource(ADS_METADATA)
    seo_source = CsvDataSource(SEO_METADATA)
    ads = ads_source.read(PROJECT_ROOT / "data" / "ads_data.csv")
    seo = seo_source.read(PROJECT_ROOT / "data" / "seo_data.csv")

    assert len(ads) == 10
    assert len(seo) == 12
    assert ads_source.last_quality_report["critical_error_count"] == 0
    assert seo_source.last_quality_report["warning_count"] == 2
    assert seo_source.last_quality_report["missing_values"]["description"] == 2
    assert ads["_source_row_number"].tolist() == list(range(2, 12))


def test_missing_file_is_reported() -> None:
    with pytest.raises(FileNotFoundError, match="data file not found"):
        CsvDataSource(ADS_METADATA).read(PROJECT_ROOT / "data" / "does_not_exist.csv")


def test_real_aggregations_recalculate_weighted_ratios() -> None:
    ads = pd.read_csv(PROJECT_ROOT / "data" / "ads_data.csv")
    seo = pd.read_csv(PROJECT_ROOT / "data" / "seo_data.csv")
    ads_result = analyze_ads(ads)
    seo_result = analyze_seo(seo)

    assert ads_result["summary"]["ctr_pct"] == round(14180 / 872000 * 100, 4)
    assert ads_result["summary"]["roas"] == round(32230 / 6680, 4)
    assert seo_result["summary"]["indexed_page_percentage"] == round(10 / 12 * 100, 4)
    assert seo_result["by_category"]


def _ads_csv(**overrides: str) -> str:
    values = {
        "campaign": "A", "platform": "Google", "campaign_type": "Search",
        "spend_usd": "100", "clicks": "10", "purchases": "1", "revenue_usd": "200",
        "impressions": "1000", "reach": "500",
    }
    values.update(overrides)
    return ",".join(values) + "\n" + ",".join(values.values()) + "\n"


def test_invalid_numeric_and_negative_values_are_critical(tmp_path: Path) -> None:
    path = tmp_path / "ads.csv"
    path.write_text(_ads_csv(spend_usd="not-a-number"), encoding="utf-8")
    with pytest.raises(DataValidationError, match="invalid_numeric"):
        CsvDataSource(ADS_METADATA).read(path)

    path.write_text(_ads_csv(spend_usd="-1"), encoding="utf-8")
    with pytest.raises(DataValidationError, match="negative_value"):
        CsvDataSource(ADS_METADATA).read(path)


def test_missing_values_are_reported_without_dropping_rows(tmp_path: Path) -> None:
    path = tmp_path / "ads.csv"
    path.write_text(_ads_csv(revenue_usd=""), encoding="utf-8")
    source = CsvDataSource(ADS_METADATA)
    frame = source.read(path)
    assert len(frame) == 1
    assert pd.isna(frame.loc[0, "revenue_usd"])
    assert source.last_quality_report["warning_count"] == 1


def test_duplicate_seo_identifiers_are_critical(tmp_path: Path) -> None:
    path = tmp_path / "seo.csv"
    row = "P-1,Product,Category,product,Description,100,5,10,True,100\n"
    path.write_text("product_id,product_name,category,url_slug,description,impressions_28d,clicks_28d,avg_position,indexed,page_load_ms\n" + row + row, encoding="utf-8")
    with pytest.raises(DataValidationError, match="duplicate_identifier"):
        CsvDataSource(SEO_METADATA).read(path)


def test_invalid_seo_values_are_critical(tmp_path: Path) -> None:
    header = "product_id,product_name,category,url_slug,description,impressions_28d,clicks_28d,avg_position,indexed,page_load_ms\n"
    row = "P-1,Product,Category,product,Description,100,5,10,True,100\n"
    path = tmp_path / "seo.csv"
    path.write_text(header + row.replace(",10,True,100", ",-1,maybe,100"), encoding="utf-8")
    with pytest.raises(DataValidationError, match="invalid_boolean|negative_value"):
        CsvDataSource(SEO_METADATA).read(path)

    path.write_text(header + row.replace(",10,True,100", ",0,True,100"), encoding="utf-8")
    with pytest.raises(DataValidationError, match="non_positive_value"):
        CsvDataSource(SEO_METADATA).read(path)

