# AI Marketing Performance Analyser

A lightweight Python 3.14 CLI for deterministic advertising and SEO analysis. It reads the current values in `data/ads_data.csv` and `data/seo_data.csv`, validates their schemas and data quality, calculates safe KPIs, emits transparent rule-based findings, and writes JSON and HTML reports.

## Quick start

Create a Python 3.14 environment, install the project and development dependencies, then run:

```powershell
python -m pip install -e ".[dev]"
marketing-analyser
```

The repository now contains the assessment datasets. The application uses their actual values and can also accept alternate files through `--ads`, `--seo`, and `--reports-dir`.

Run tests with `pytest`.

## OpenRouter integration

The project includes an optional recommendation stage through `marketing_analyzer.llm`. OpenRouter uses an OpenAI-compatible Chat Completions endpoint. The default model is `openrouter/auto`; set `OPENROUTER_MODEL` to pin a specific provider/model slug when reproducibility is required. The LLM receives only prioritised deterministic findings and must return validated, finding-linked recommendations.

Configure the existing key through the environment or an untracked `.env` file:

```powershell
$env:OPENROUTER_API_KEY = "your-key-value"
$env:OPENROUTER_MODEL = "openrouter/auto"
```

The CLI loads the project-root `.env` before creating the provider. The project-root file takes precedence over a stale process-level `OPENROUTER_API_KEY`, which avoids silently sending an old terminal value. A 401 response means the supplied credential was present but rejected by OpenRouter; the application reports a safe authentication message without printing the key.

Never place the key in source code, `.env.example`, tests, or GitHub workflow files. The deterministic CLI does not call the provider automatically; recommendation generation remains an explicit next integration step.

Enable the opt-in stage with:

```powershell
python -m marketing_analyzer.cli --recommendations --llm-endpoint openrouter_default --llm-model openrouter/auto
```

Supported endpoint profiles are `openrouter_default`, `openai_direct`, `gemini_direct`, and `custom_openai_compatible`. CLI values override environment configuration. Set `LLM_ENDPOINT_PROFILE`, `LLM_PROVIDER`, `LLM_TIMEOUT`, `LLM_MAX_RETRIES`, and `LLM_TEMPERATURE` in `.env` or the shell. Missing credentials result in `skipped_due_to_configuration`; malformed responses or provider failures result in `failed`, while deterministic reports are preserved.

## Design notes

- `data_sources` owns ingestion and schema metadata; future connectors can implement `DataSource`.
- Ingestion preserves each input record's CSV row as `_source_row_number` and exposes data-quality findings in the report.
- Critical issues (missing required columns, invalid numeric/boolean values, negative values, invalid search positions, and duplicate SEO product IDs) stop analysis with `DataValidationError`.
- Warnings (such as missing descriptions) are reported without dropping rows. Legitimate zero values are retained as noteworthy values; zero denominators produce unavailable ratios.
- `data_processing.metrics` owns denominator-safe KPI calculations. Zero denominators produce `NaN`/`None`, not false zero performance.
- `analysis` creates dataset-specific summaries using weighted aggregate ratios; `insights.rules` contains explainable current-state rules.
- `llm` contains the provider interface, named endpoint registry, OpenRouter/OpenAI-compatible adapters, Gemini REST adapter, structured Pydantic recommendations, and an injectable HTTP client for offline tests.
- Authentication failures preserve deterministic reports and are recorded as `failed`; missing credentials are recorded as `skipped_due_to_configuration`.
- Reports include data-quality summaries and explicitly state that these inputs are aggregates and do not support historical trend claims.

## Marketing intelligence and prioritisation

Findings are current-state, deterministic records. Advertising rules cover upper-quartile spend, CPA, CPC, revenue and ROAS, below-median ROAS/conversion/CTR, and campaign-level evidence. SEO rules cover high-impression below-peer CTR, non-indexed pages, weaker relative positions, slower relative load times, and strong visibility. Comparisons are limited to the supplied dataset; no industry benchmark or historical trend is inferred.

Each finding has a stable ID, source dataset/entity, evidence, supporting metrics, limitations, recommended action, impact score and priority score. Scores use configurable weights: potential business impact 35%, financial exposure/opportunity 25%, reach/visibility 20%, actionability 10%, evidence confidence 10%. Scores are bounded to 0–100; missing factors are excluded and remaining weights renormalised. Priority categories are Critical (80+), High (60–79.99), Medium (35–59.99), and Low (below 35).

AI recommendations are separately marked from deterministic findings and require evidence, valid finding IDs, action, qualitative outcome, measurement method, effort, confidence, assumptions and limitations. The action plan groups validated recommendations into immediate, short-term optimisation and longer-term opportunities without inventing deadlines.

### Recommendation reliability and human review

Recommendation prompts are versioned separately from providers. The current prompt version is `recommendations-v2` and is recorded in each report. It explicitly defines required JSON array and field types after the live model returned string/null values for fields requiring strings/lists. The provider classifies safe failures as `authentication_error`, `model_unavailable`, `insufficient_credits`, `rate_limit`, `network_error`, `provider_error`, `empty_response`, or `invalid_json`; validation adds `schema_validation_error` and `invalid_finding_reference`. Schema diagnostics record only field paths and error types, never raw model output or credentials.

Generated recommendations are always assigned `pending_review`. Review decisions are persisted in `reports/recommendation_reviews.json`, so regenerating a report does not erase human decisions. Inspect recommendations with:

```powershell
python -m marketing_analyzer.cli --inspect-recommendations
python -m marketing_analyzer.cli --review-rec rec-1 --review-status approved --review-note "Evidence checked"
python -m marketing_analyzer.cli --no-recommendations
```

Supported review states are `pending_review`, `approved`, `rejected`, and `needs_revision`. No review command makes an LLM call.

## HTML dashboard

The generated HTML report is a responsive, print-friendly stakeholder dashboard. It renders advertising and SEO KPI cards from the report data, finding severity/type counts, evidence-backed findings, recommendation review states, input filenames and SHA-256 hashes, prompt/provider metadata, data quality and limitations. Jinja2 autoescaping remains enabled; CSV text is not trusted as HTML. Missing optional metrics render as `Unavailable` rather than fabricated zeroes.

## Dynamic refresh and safe publication

Every analysis execution rereads and validates both CSV files, recalculates KPIs/findings, and regenerates both reports. Each input fingerprint records filename, SHA-256, byte size, UTC modification time, row count and column count. The report compares current hashes with the previous valid report and records whether advertising, SEO, both, or neither dataset changed. A file that changes while it is being read aborts before report publication.

The generated JSON report is `reports/marketing_report.json`; the HTML report is `reports/marketing_report.html`. Inspect the JSON report safely with:

```powershell
python -m marketing_analyzer.cli --inspect-recommendations
```

This prints the resolved path, existence, recommendation status, safe error category and recommendation count. It distinguishes a missing report from invalid JSON. `reports/report.json` is not an application output filename.

JSON and HTML are rendered from the same analysis result, written to temporary files, validated, and atomically replaced with rollback protection. If report publication fails, the previous valid report is preserved. Review decisions include a recommendation content fingerprint; changed or removed recommendations do not inherit old approvals, while unchanged recommendations retain their review status.

An earlier controlled live OpenRouter verification exposed a schema compatibility issue. After the `recommendations-v2` prompt correction, the current report contains 9 validated recommendations from `openai/gpt-4.1-mini`. They remain `pending_review`; no recommendation is automatically approved.

Normal workflows:

```powershell
python -m marketing_analyzer.cli
python -m marketing_analyzer.cli --recommendations
python -m marketing_analyzer.cli --ads path\ads_data.csv --seo path\seo_data.csv --reports-dir reports
```

## Handover for the next agent

1. Review the generated recommendations with `--inspect-recommendations` and record decisions with `--review-rec`.
2. Run the offline regression suite before submission.
3. Add historical source data only if trend analysis becomes a requirement.

GitHub Actions CI is configured in `.github/workflows/ci.yml` for Python 3.14. It installs the editable project with development dependencies, compiles source and tests, and runs pytest without making external LLM calls.

