from pathlib import Path

from marketing_analyzer.pipeline import run_analysis


def test_pipeline_writes_reports(tmp_path: Path) -> None:
    ads = tmp_path / "ads.csv"
    seo = tmp_path / "seo.csv"
    ads.write_text("campaign,platform,campaign_type,spend_usd,clicks,purchases,revenue_usd,impressions,reach\nA,Search,Brand,100,20,2,400,1000,800\n", encoding="utf-8")
    seo.write_text("product_id,product_name,category,url_slug,description,impressions_28d,clicks_28d,avg_position,indexed,page_load_ms\n1,One,Cat,one,Desc,1000,5,12,True,1200\n", encoding="utf-8")
    report = run_analysis(ads, seo, tmp_path / "reports")
    assert report["ads"]["campaigns"][0]["roas"] == 4.0
    assert (tmp_path / "reports" / "marketing_report.json").exists()
    assert (tmp_path / "reports" / "marketing_report.html").exists()

