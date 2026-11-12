# Project Status

**Project:** AI Marketing Performance Analyser  
**Status:** Phase 5 final regression audit complete; deterministic analysis and current OpenRouter recommendation generation are verified. Recommendations remain pending human review.  
**Target runtime:** Python 3.14  
**Application type:** Command-line application

## Summary

The project now reads the supplied assessment CSV inputs, validates their required schemas and values, calculates deterministic KPIs, creates current-state findings, and writes JSON and HTML reports with data-quality summaries.

No business metrics or historical trends are fabricated. All reported values come from the current CSV files.

## Actual dataset profile

### Advertising dataset

- File: `data/ads_data.csv`
- Records: 10
- Columns: 9
- Columns: `campaign`, `platform`, `campaign_type`, `spend_usd`, `clicks`, `purchases`, `revenue_usd`, `impressions`, `reach`
- Numeric columns were read as integer values and contain no missing, negative, or invalid values.
- Duplicate records: 0.
- Observed ranges: spend 240–1,120 USD; clicks 700–2,240; purchases 14–48; revenue 1,540–5,760 USD; impressions 18,500–168,000; reach 650–8,200.
- Aggregate values: spend 6,680 USD, revenue 32,230 USD, clicks 14,180, purchases 286, impressions 872,000, reach 43,600.

### SEO dataset

- File: `data/seo_data.csv`
- Records: 12
- Columns: 10
- Columns: `product_id`, `product_name`, `category`, `url_slug`, `description`, `impressions_28d`, `clicks_28d`, `avg_position`, `indexed`, `page_load_ms`
- Numeric columns contain no invalid or negative values.
- Duplicate records: 0; duplicate product identifiers: 0.
- Missing values: 2 missing `description` values; no missing identifiers or KPI inputs.
- `indexed` values are consistently boolean.
- Observed ranges: impressions 6,100–52,000; clicks 61–954; average position 3.8–22.4; page load 46–96 ms.

## Current calculated summaries

- Advertising: CTR 1.6261%, CPC 0.4711 USD, CPA 23.3566 USD, ROAS 4.8249, conversion rate 2.0169%, CPM 7.6606 USD, frequency 20.0.
- SEO: average position 11.2083, indexed-page percentage 83.3333%, non-indexed pages 2, average page load 68.0833 ms.
- The current run produces 37 deterministic findings using peer-relative advertising and SEO rules. Counts are data-derived and recalculate when the CSV inputs change.

## Implemented

- Configuration through environment variables and `.env` support.
- CSV ingestion with required-column validation and numeric coercion.
- Data-quality reports with critical errors, warnings, noteworthy values, missing-value counts, duplicate checks, and source-row traceability.
- Critical validation for invalid numeric/boolean values, negative advertising inputs, invalid SEO positions/page-load inputs, and duplicate SEO product IDs.
- Warning-level handling for missing non-identifier values without silently dropping records.
- Boolean parsing for the SEO `indexed` field.
- Advertising KPIs:
  - CTR
  - CPC
  - CPA
  - ROAS
  - Conversion rate
  - CPM
  - Frequency
- SEO metrics:
  - Organic CTR
  - Average search position
  - Indexed-page percentage
  - Non-indexed page count
  - Average page-load time
- Platform, campaign-type, and SEO-category summaries.
- Peer-relative findings for high spend, low/high ROAS, high CPA/CPC, below-peer conversion/CTR, meaningful revenue, high-impression low-CTR pages, non-indexed pages, weak/strong visibility and slow-loading pages.
- Pydantic finding models with stable IDs, source-row evidence, supporting metrics, business interpretation, limitations and recommended actions.
- Transparent configurable impact and priority scoring with documented factor weights and priority categories.
- Executive summary, highest-priority findings/opportunities, score explanations and recommendation action-plan sections in reports.
- Safe zero-denominator handling using missing values instead of false zero performance.
- JSON and Jinja2 HTML report generation.
- Provider-agnostic `LLMProvider` interface for future recommendation generation.
- CLI options for custom ads, SEO, and report paths.
- Initial tests for metrics, source validation, and report generation.
- Dependency declarations in both `pyproject.toml` and `requirements.txt`.
- OpenRouter integration through `OpenRouterProvider`, using `OPENROUTER_API_KEY` and configurable `OPENROUTER_MODEL`.
- Optional recommendation execution through `--recommendations` or `ENABLE_AI_RECOMMENDATIONS=true`; normal execution remains offline.
- Named endpoint profiles for OpenRouter, OpenAI direct, Gemini direct, and custom OpenAI-compatible endpoints.
- Provider-specific adapters, configurable model/base URL/key, timeout, retry count, and temperature.
- Pydantic recommendation schema with finding-reference validation and explicit recommendation status.
- Offline mocked provider tests with no external API calls.
- Project-root `.env` loading takes precedence over stale process-level credential values; authentication errors are safe and secret-free.
- GitHub Actions CI for Python 3.14 dependency installation, compilation, and pytest.
- Versioned recommendation prompt `recommendations-v2`, recorded in report metadata, with explicit JSON field-type examples for model compatibility.
- Safe provider error categories for authentication, model availability, credits, rate limits, network/provider failures, empty/invalid responses, schema failures and invalid finding references.
- Persistent human review decisions in `reports/recommendation_reviews.json`, with `pending_review` as the default and CLI inspection/review commands.
- Responsive, print-friendly HTML dashboard with data-driven advertising/SEO KPI cards, finding counts, review-state styling, provenance hashes, empty states and safe Jinja2 escaping.
- SEO summary now includes weighted aggregate impressions, clicks and organic CTR for dashboard rendering.
- Dynamic refresh now records filename, SHA-256, file size, modification timestamp, row count and column count for each input; prior successful report fingerprints drive changed/unchanged metadata.
- JSON and HTML are prepared from the same result and published through temporary files with rollback protection; input changes detected during processing abort before report publication.

## Project layout

```text
data/                         Input CSV templates
src/marketing_analyzer/       Application source
  analysis/                   Dataset-specific analysis
  config/                     Runtime settings
  data_processing/            KPI calculations
  data_sources/               Input adapters and schemas
  insights/                   Deterministic rules
  llm/                        LLM provider boundary and OpenRouter adapter
  reporting/                  JSON and HTML output
tests/                        Automated tests
reports/                      Generated report output
```

## Current limitations

- Recommendation generation is opt-in and requires provider credentials; normal execution remains deterministic and offline.
- An earlier controlled live OpenRouter run exposed a schema compatibility issue. After the `recommendations-v2` prompt correction, the current report contains 9 validated recommendations from `openai/gpt-4.1-mini`; credentials and raw provider responses are not exposed.
- OpenRouter models may differ in JSON adherence; the current provider uses concise prompt-only JSON with a configurable `response_format` parser mode (`json` or `json_markdown`) rather than assuming provider-specific structured-output support.
- Reports include recommendation status, provider/profile/model metadata, validated recommendations, action-plan groups, and schema version `1.2`.
- Historical trend analysis is intentionally unavailable because the supplied dataset design is aggregate/current-state data; this cannot be fixed without historical source data.
- Advertising duplicate campaign names are not treated as automatically invalid because repeated campaign names may represent separate records; the current dataset contains no duplicate full records.

## How to run

Activate the project environment and install dependencies:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Replace the headers-only files with the real datasets, then run:

```powershell
python -m marketing_analyzer.cli
```

If the package has been installed in editable mode, the console command is also available:

```powershell
marketing-analyser
```

Custom input and output paths are supported:

```powershell
python -m marketing_analyzer.cli --ads path\ads_data.csv --seo path\seo_data.csv --reports-dir reports
```

## Verification status

- Python 3.14.2 was verified in the development environment.
- Source compilation completed successfully.
- VS Code diagnostics reported no errors in the source and test directories.
- The CLI smoke test completed successfully with the empty CSV templates.
- The project `.venv` test run passes all current tests: `47 passed` using `python -m pytest -q -p no:cacheprovider`.
- The CLI was run against the actual files and reported: `Analysed 10 advertising rows and 12 SEO rows.`
- A later live recommendation verification using `openai/gpt-4.1-mini` generated 9 validated recommendations. The report inspection command confirms `Status: generated`, `Error: None`, 9 recommendations, valid finding references and `pending_review` states. No credential or raw response was exposed.
- Offline authentication diagnostics verified that the provider constructs a Bearer header and returns a safe HTTP 401 message without exposing credentials.
- Pytest's cache provider emitted a Windows permission/cache-path warning in the existing `.pytest_cache`; the verified command used `-p no:cacheprovider` to avoid relying on that stale generated cache.
- Final audit verified the advertising and SEO KPI formulas against the real report output, including weighted aggregate ratios and zero-denominator behavior.
- Temporary-copy refresh demonstration verified advertising-only changes, SEO-only changes, both-file changes, unchanged inputs, recalculated KPIs/findings, regenerated JSON/HTML, concurrent-change protection and review fingerprint behavior.
- The supplied datasets contain current aggregate data rather than historical snapshots, so trend claims remain unavailable. AI recommendations are generated successfully but must be human-reviewed before approval.

## Recommended next steps

1. Review the 9 generated recommendations manually using the persisted review workflow.
2. Run the offline regression suite before submission.
3. Add optional historical data sources if trend analysis becomes a requirement.

## Next-session handover

### Projected status

The next session should begin from a stable Phase 5 baseline:

- Deterministic analysis, validation, KPI calculations, findings, scoring and reports are implemented.
- Dynamic CSV refresh, SHA-256 provenance and changed/unchanged dataset detection are implemented.
- JSON/HTML publication uses temporary files with rollback protection.
- Canonical report outputs are `reports/marketing_report.json` and `reports/marketing_report.html`; the CLI inspection command reports resolved paths and distinguishes missing files from invalid JSON.
- Human review decisions use recommendation content fingerprints and default to `pending_review`.
- The offline suite is green at 47 tests.
- The latest generated report contains 9 validated recommendations from `openai/gpt-4.1-mini`; all 9 remain `pending_review` until a human reviews them.

### First actions for the next session

1. Read this document and confirm the workspace remains on the Phase 4 baseline.
2. Run `python -m pytest -q -p no:cacheprovider` and `python -m compileall -q src tests`.
3. Review the generated recommendation report and persisted review file.
4. If a fresh live verification is required, run one controlled command:

   ```powershell
   python -m marketing_analyzer.cli --recommendations
   ```

5. Inspect only safe report metadata: `recommendations_status`, `recommendations_error_category`, recommendation count, finding references and review states.
6. If recommendations are generated, review them with `--inspect-recommendations` and record decisions with `--review-rec`.
7. Do not modify the supplied assessment CSV files; use temporary copies for refresh or failure tests.

### Important constraints

- Do not claim live recommendation success unless the report contains validated recommendations from an actual provider response.
- Do not print or log API keys, authorization headers or raw provider error bodies.
- Do not infer historical trends from the current aggregate datasets.
- Do not automatically transfer human approval to a materially changed recommendation.

