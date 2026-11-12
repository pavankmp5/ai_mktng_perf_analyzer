"""Schema metadata for supported datasets."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceMetadata:
    name: str
    required_columns: tuple[str, ...]
    numeric_columns: tuple[str, ...]
    identifier_columns: tuple[str, ...] = ()
    non_negative_columns: tuple[str, ...] = ()
    positive_columns: tuple[str, ...] = ()
    boolean_columns: tuple[str, ...] = ()
    unique_columns: tuple[str, ...] = ()


ADS_METADATA = SourceMetadata(
    "ads",
    ("campaign", "platform", "campaign_type", "spend_usd", "clicks", "purchases", "revenue_usd", "impressions", "reach"),
    ("spend_usd", "clicks", "purchases", "revenue_usd", "impressions", "reach"),
    non_negative_columns=("spend_usd", "clicks", "purchases", "revenue_usd", "impressions", "reach"),
)
SEO_METADATA = SourceMetadata(
    "seo",
    ("product_id", "product_name", "category", "url_slug", "description", "impressions_28d", "clicks_28d", "avg_position", "indexed", "page_load_ms"),
    ("impressions_28d", "clicks_28d", "avg_position", "page_load_ms"),
    identifier_columns=("product_id",),
    non_negative_columns=("impressions_28d", "clicks_28d", "page_load_ms"),
    positive_columns=("avg_position",),
    boolean_columns=("indexed",),
    unique_columns=("product_id",),
)

