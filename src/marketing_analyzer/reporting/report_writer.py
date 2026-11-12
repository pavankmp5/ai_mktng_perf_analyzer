"""Validated, atomic publication of the paired report files."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape


def write_reports(report: dict, reports_dir: Path) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    environment = Environment(loader=PackageLoader("marketing_analyzer", "templates"), autoescape=select_autoescape())
    json_text = json.dumps(report, indent=2, default=_json_default)
    html_text = environment.get_template("report.html").render(report=report)
    if not json.loads(json_text) or not html_text.strip():
        raise ValueError("Generated report output failed validation")
    json_path = reports_dir / "marketing_report.json"
    html_path = reports_dir / "marketing_report.html"
    json_tmp: Path | None = None
    html_tmp: Path | None = None
    backups: list[tuple[Path, Path]] = []
    try:
        json_tmp = _write_temp(reports_dir, json_text)
        html_tmp = _write_temp(reports_dir, html_text)
        for target in (json_path, html_path):
            if target.exists():
                descriptor, backup_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".bak", dir=reports_dir)
                os.close(descriptor)
                backup = Path(backup_name)
                backup.write_bytes(target.read_bytes())
                backups.append((target, backup))
        os.replace(json_tmp, json_path)
        os.replace(html_tmp, html_path)
    except Exception:
        for target, backup in backups:
            os.replace(backup, target)
        raise
    finally:
        for temporary in (json_tmp, html_tmp):
            if temporary is not None and temporary.exists():
                temporary.unlink()
        for _, backup in backups:
            if backup.exists():
                backup.unlink()


def _write_temp(directory: Path, content: str) -> Path:
    descriptor, name = tempfile.mkstemp(prefix=".marketing-report-", suffix=".tmp", dir=directory, text=True)
    path = Path(name)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    return path


def _json_default(value: object) -> object:
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)
