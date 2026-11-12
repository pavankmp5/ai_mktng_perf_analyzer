"""Human-readable HTML report output."""

from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape


def write_html(report: dict, path: Path) -> None:
    environment = Environment(loader=PackageLoader("marketing_analyzer", "templates"), autoescape=select_autoescape())
    html = environment.get_template("report.html").render(report=report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")

 