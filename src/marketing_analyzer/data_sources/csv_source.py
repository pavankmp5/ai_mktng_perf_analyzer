"""CSV ingestion, schema validation, and light cleaning."""

from pathlib import Path
from dataclasses import dataclass
from typing import Any

import pandas as pd

from .base_source import DataSource
from .source_metadata import SourceMetadata


class DataValidationError(ValueError):
    """Raised when an input file cannot satisfy its declared schema."""

    def __init__(self, message: str, quality_report: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.quality_report = quality_report


@dataclass(frozen=True)
class DataQualityIssue:
    severity: str
    code: str
    message: str
    column: str | None = None
    count: int = 1


@dataclass(frozen=True)
class DataQualityReport:
    dataset: str
    row_count: int
    column_count: int
    missing_values: dict[str, int]
    duplicate_rows: int
    issues: tuple[DataQualityIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "missing_values": self.missing_values,
            "duplicate_rows": self.duplicate_rows,
            "issues": [issue.__dict__ for issue in self.issues],
            "critical_error_count": sum(issue.count for issue in self.issues if issue.severity == "critical"),
            "warning_count": sum(issue.count for issue in self.issues if issue.severity == "warning"),
            "noteworthy_count": sum(issue.count for issue in self.issues if issue.severity == "noteworthy"),
        }


class CsvDataSource(DataSource):
    def __init__(self, metadata: SourceMetadata) -> None:
        self.metadata = metadata
        self.last_quality_report: dict[str, Any] | None = None

    def read(self, path: Path) -> pd.DataFrame:
        if not path.exists():
            raise FileNotFoundError(f"{self.metadata.name} data file not found: {path}")
        raw = pd.read_csv(path)
        missing = [column for column in self.metadata.required_columns if column not in raw.columns]
        if missing:
            raise DataValidationError(f"{self.metadata.name} data is missing columns: {', '.join(missing)}")
        frame = raw.loc[:, list(self.metadata.required_columns)].copy()
        frame.insert(0, "_source_row_number", range(2, len(frame) + 2))
        issues: list[DataQualityIssue] = []

        for column in self.metadata.identifier_columns:
            missing_ids = frame[column].isna() | frame[column].astype(str).str.strip().eq("")
            if missing_ids.any():
                issues.append(DataQualityIssue("critical", "missing_identifier", f"{int(missing_ids.sum())} missing identifier value(s)", column, int(missing_ids.sum())))

        for column in self.metadata.numeric_columns:
            original = frame[column]
            parsed = pd.to_numeric(original, errors="coerce")
            invalid = original.notna() & parsed.isna()
            if invalid.any():
                issues.append(DataQualityIssue("critical", "invalid_numeric", f"{int(invalid.sum())} non-numeric value(s)", column, int(invalid.sum())))
            if original.isna().any():
                issues.append(DataQualityIssue("warning", "missing_value", f"{int(original.isna().sum())} missing value(s)", column, int(original.isna().sum())))
            if column in self.metadata.non_negative_columns:
                negative = parsed < 0
                if negative.any():
                    issues.append(DataQualityIssue("critical", "negative_value", f"{int(negative.sum())} negative value(s)", column, int(negative.sum())))
            if column in self.metadata.positive_columns:
                invalid_positive = parsed <= 0
                if invalid_positive.any():
                    issues.append(DataQualityIssue("critical", "non_positive_value", f"{int(invalid_positive.sum())} non-positive value(s)", column, int(invalid_positive.sum())))
            if (parsed == 0).any():
                issues.append(DataQualityIssue("noteworthy", "zero_value", f"{int((parsed == 0).sum())} zero value(s) are present and retained", column, int((parsed == 0).sum())))
            frame[column] = parsed

        for column in self.metadata.boolean_columns:
            parsed = frame[column].map(_parse_bool)
            invalid = frame[column].notna() & parsed.isna()
            if invalid.any():
                issues.append(DataQualityIssue("critical", "invalid_boolean", f"{int(invalid.sum())} invalid boolean value(s)", column, int(invalid.sum())))
            if frame[column].isna().any():
                issues.append(DataQualityIssue("warning", "missing_value", f"{int(frame[column].isna().sum())} missing value(s)", column, int(frame[column].isna().sum())))
            frame[column] = parsed.astype("boolean")

        for column in self.metadata.required_columns:
            if column not in self.metadata.numeric_columns and column not in self.metadata.boolean_columns and frame[column].isna().any():
                severity = "critical" if column in self.metadata.identifier_columns else "warning"
                issues.append(DataQualityIssue(severity, "missing_value", f"{int(frame[column].isna().sum())} missing value(s)", column, int(frame[column].isna().sum())))

        duplicates = int(frame.duplicated(subset=list(self.metadata.required_columns)).sum())
        if duplicates:
            issues.append(DataQualityIssue("warning", "duplicate_record", f"{duplicates} duplicate record(s)", count=duplicates))
        for column in self.metadata.unique_columns:
            duplicates = int(frame[column].duplicated(keep=False).sum())
            if duplicates:
                issues.append(DataQualityIssue("critical", "duplicate_identifier", f"{duplicates} duplicate identifier row(s)", column, duplicates))

        quality = DataQualityReport(self.metadata.name, len(frame), len(self.metadata.required_columns), frame[list(self.metadata.required_columns)].isna().sum().astype(int).to_dict(), int(frame.duplicated(subset=list(self.metadata.required_columns)).sum()), tuple(issues))
        self.last_quality_report = quality.to_dict()
        critical = [issue for issue in issues if issue.severity == "critical"]
        if critical:
            summary = "; ".join(issue.code + ": " + issue.message + (f" in {issue.column}" if issue.column else "") for issue in critical)
            raise DataValidationError(f"{self.metadata.name} data has critical quality errors: {summary}", self.last_quality_report)
        return frame


def _parse_bool(value: object) -> bool | None:
    if pd.isna(value):
        return None
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None

