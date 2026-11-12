from pathlib import Path

import pytest

from marketing_analyzer.data_sources.csv_source import CsvDataSource, DataValidationError
from marketing_analyzer.data_sources.source_metadata import ADS_METADATA


def test_csv_source_rejects_missing_columns(tmp_path: Path) -> None:
    path = tmp_path / "ads.csv"
    path.write_text("campaign,platform\nA,Search\n", encoding="utf-8")
    with pytest.raises(DataValidationError, match="missing columns"):
        CsvDataSource(ADS_METADATA).read(path)

