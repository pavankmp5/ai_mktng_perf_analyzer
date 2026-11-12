"""Typed application settings loaded from environment variables."""

from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field


class Settings(BaseModel):
    """Runtime settings; paths are resolved relative to the project directory."""

    model_config = ConfigDict(extra="ignore")

    ads_data_path: Path = Field(default=Path("data/ads_data.csv"))
    seo_data_path: Path = Field(default=Path("data/seo_data.csv"))
    reports_dir: Path = Field(default=Path("reports"))
    log_level: str = "INFO"


def load_settings(project_dir: Path | None = None) -> Settings:
    """Load .env values and return settings with paths rooted at ``project_dir``."""

    root = (project_dir or _default_project_root()).resolve()
    # This application treats the project-root .env as the local source of truth.
    # It prevents a stale terminal variable from silently replacing the intended key.
    # CI should not create a .env file; repository secrets remain available there.
    load_dotenv(root / ".env", override=True)
    settings = Settings(
        ads_data_path=Path(__import__("os").getenv("ADS_DATA_PATH", "data/ads_data.csv")),
        seo_data_path=Path(__import__("os").getenv("SEO_DATA_PATH", "data/seo_data.csv")),
        reports_dir=Path(__import__("os").getenv("REPORTS_DIR", "reports")),
        log_level=__import__("os").getenv("LOG_LEVEL", "INFO"),
    )
    return settings.model_copy(update={
        "ads_data_path": _root_path(root, settings.ads_data_path),
        "seo_data_path": _root_path(root, settings.seo_data_path),
        "reports_dir": _root_path(root, settings.reports_dir),
    })


def _root_path(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def _default_project_root() -> Path:
    """Prefer the repository root when the CLI is launched outside it."""

    current = Path.cwd().resolve()
    if (current / ".env").exists() or (current / "pyproject.toml").exists():
        return current
    source_root = Path(__file__).resolve().parents[3]
    return source_root if (source_root / "pyproject.toml").exists() else current

