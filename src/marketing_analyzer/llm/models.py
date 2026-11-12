"""Validated recommendation models exchanged with LLM providers."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RecommendationPriority(StrEnum):
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class RecommendationReviewStatus(StrEnum):
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"


class Recommendation(BaseModel):
    """A recommendation grounded in one or more deterministic findings."""

    model_config = ConfigDict(extra="forbid")

    recommendation_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    category: str = Field(min_length=1)
    description: str = Field(min_length=1)
    related_finding_ids: list[str] = Field(min_length=1)
    priority: RecommendationPriority
    evidence: list[str] = Field(min_length=1)
    suggested_action: str = Field(min_length=1)
    expected_business_outcome: str = Field(min_length=1)
    measurement_method: str = Field(min_length=1)
    implementation_effort: str = Field(min_length=1)
    confidence: str = Field(pattern="^(high|medium|low)$")
    assumptions: list[str] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    review_status: RecommendationReviewStatus = RecommendationReviewStatus.PENDING_REVIEW
    reviewer_note: str = ""

