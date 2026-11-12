import os
from pathlib import Path

from marketing_analyzer.config.settings import load_settings


def test_project_root_env_overrides_stale_process_value(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / ".env").write_text("OPENROUTER_API_KEY=project-key\n", encoding="utf-8")
    monkeypatch.setenv("OPENROUTER_API_KEY", "stale-terminal-value")
    load_settings(tmp_path)
    assert os.environ["OPENROUTER_API_KEY"] == "project-key"


def test_default_settings_use_repository_root_when_launched_elsewhere(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    settings = load_settings()
    assert settings.ads_data_path.name == "ads_data.csv"
    assert settings.ads_data_path.parent.name == "data"
    assert settings.reports_dir.name == "reports"
