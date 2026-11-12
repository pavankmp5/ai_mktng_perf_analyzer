"""Validated deterministic finding model."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class FindingSeverity(StrEnum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    finding_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    source_dataset: str = Field(min_length=1)
    entity_name: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    severity: FindingSeverity
    impact_score: float = Field(ge=0, le=100)
    priority_score: float = Field(ge=0, le=100)
    supporting_metrics: dict[str, float | int | str | bool | None]
    evidence: list[str] = Field(min_length=1)
    business_interpretation: str = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    recommended_action: str = Field(min_length=1)

    # Compatibility fields retained for existing report consumers.
    dataset: str
    type: str
    priority: str
    title_legacy: str | None = None
    detail: str | None = None
    entity: str | None = None
    priority_factors: dict[str, float | None] = Field(default_factory=dict)

    def to_report_dict(self) -> dict:
        value = self.model_dump(mode="json", exclude_none=True)
        value["title"] = self.title
        value["detail"] = self.description
        value["entity"] = self.entity_name
        return value

