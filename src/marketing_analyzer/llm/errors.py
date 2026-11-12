"""Safe, structured recommendation-stage error categories."""

from enum import StrEnum


class RecommendationErrorCategory(StrEnum):
    AUTHENTICATION_ERROR = "authentication_error"
    MODEL_UNAVAILABLE = "model_unavailable"
    INSUFFICIENT_CREDITS = "insufficient_credits"
    RATE_LIMIT = "rate_limit"
    NETWORK_ERROR = "network_error"
    PROVIDER_ERROR = "provider_error"
    EMPTY_RESPONSE = "empty_response"
    INVALID_JSON = "invalid_json"
    SCHEMA_VALIDATION_ERROR = "schema_validation_error"
    INVALID_FINDING_REFERENCE = "invalid_finding_reference"
