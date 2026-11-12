"""Registry for adding new source types without changing the pipeline."""

from .csv_source import CsvDataSource
from .source_metadata import ADS_METADATA, SEO_METADATA


def default_sources() -> dict[str, CsvDataSource]:
    return {"ads": CsvDataSource(ADS_METADATA), "seo": CsvDataSource(SEO_METADATA)}

