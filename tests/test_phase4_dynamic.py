from pathlib import Path

import pytest

from marketing_analyzer.pipeline import run_analysis
from marketing_analyzer.reporting.report_writer import write_reports


ROOT = Path(__file__).parents[1]


def _copies(tmp_path: Path) -> tuple[Path, Path, Path]:
    ads = tmp_path / "ads.csv"
    seo = tmp_path / "seo.csv"
    ads.write_bytes((ROOT / "data/ads_data.csv").read_bytes())
    seo.write_bytes((ROOT / "data/seo_data.csv").read_bytes())
    return ads, seo, tmp_path / "reports"


def test_dynamic_ad_update_recalculates_kpis_and_detects_hash_change(tmp_path: Path) -> None:
    ads, seo, reports = _copies(tmp_path)
    first = run_analysis(ads, seo, reports)
    ads.write_text(ads.read_text(encoding="utf-8").replace("Search,620,", "Search,1620,"), encoding="utf-8")
    second = run_analysis(ads, seo, reports)
    assert first["ads"]["summary"]["spend_usd"] == 6680
    assert second["ads"]["summary"]["spend_usd"] == 7680
    assert second["change_detection"]["ads"]["status"] == "changed"
    assert second["change_detection"]["seo"]["status"] == "unchanged"
    assert second["provenance"]["ads"]["sha256"] != first["provenance"]["ads"]["sha256"]


def test_dynamic_seo_update_and_unchanged_run(tmp_path: Path) -> None:
    ads, seo, reports = _copies(tmp_path)
    first = run_analysis(ads, seo, reports)
    unchanged = run_analysis(ads, seo, reports)
    seo.write_text(seo.read_text(encoding="utf-8").replace(",52000,410,", ",52000,1410,"), encoding="utf-8")
    changed = run_analysis(ads, seo, reports)
    assert unchanged["change_detection"]["any_changed"] is False
    assert changed["change_detection"]["seo"]["status"] == "changed"
    assert changed["seo"]["summary"]["organic_ctr_pct"] != first["seo"]["summary"]["organic_ctr_pct"]
    assert changed["change_detection"]["ads"]["status"] == "unchanged"


def test_both_inputs_changed_are_recorded(tmp_path: Path) -> None:
    ads, seo, reports = _copies(tmp_path)
    run_analysis(ads, seo, reports)
    ads.write_text(ads.read_text(encoding="utf-8").replace("Search,620,", "Search,1620,"), encoding="utf-8")
    seo.write_text(seo.read_text(encoding="utf-8").replace(",52000,410,", ",52000,1410,"), encoding="utf-8")
    report = run_analysis(ads, seo, reports)
    assert report["change_detection"]["both_changed"] is True
    assert report["change_detection"]["any_changed"] is True


def test_concurrent_input_change_aborts_before_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ads, seo, reports = _copies(tmp_path)
    run_analysis(ads, seo, reports)
    original = (reports / "marketing_report.json").read_text(encoding="utf-8")
    import marketing_analyzer.pipeline as pipeline

    real_fingerprint = pipeline.fingerprint_file
    calls = {"ads": 0}

    def changing_fingerprint(path: Path, row_count: int, column_count: int) -> dict:
        result = real_fingerprint(path, row_count, column_count)
        if path == ads:
            calls["ads"] += 1
            if calls["ads"] == 2:
                result["sha256"] = "changed-during-read"
        return result

    monkeypatch.setattr(pipeline, "fingerprint_file", changing_fingerprint)
    with pytest.raises(RuntimeError, match="changed while it was being analysed"):
        run_analysis(ads, seo, reports)
    assert (reports / "marketing_report.json").read_text(encoding="utf-8") == original


def test_atomic_writer_preserves_existing_reports_when_publication_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    report = run_analysis(ROOT / "data/ads_data.csv", ROOT / "data/seo_data.csv", tmp_path)
    write_reports(report, tmp_path)
    original_json = (tmp_path / "marketing_report.json").read_text(encoding="utf-8")
    original_html = (tmp_path / "marketing_report.html").read_text(encoding="utf-8")
    real_replace = __import__("os").replace
    calls = 0

    def fail_second(source: str | bytes | Path, target: str | bytes | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated interruption")
        real_replace(source, target)

    monkeypatch.setattr("marketing_analyzer.reporting.report_writer.os.replace", fail_second)
    with pytest.raises(OSError, match="simulated interruption"):
        changed_report = dict(report)
        changed_report["generated_at"] = "changed"
        write_reports(changed_report, tmp_path)
    assert (tmp_path / "marketing_report.json").read_text(encoding="utf-8") == original_json
    assert (tmp_path / "marketing_report.html").read_text(encoding="utf-8") == original_html
