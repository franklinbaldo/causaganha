# Contributing to CausaGanha

Thank you for your interest in contributing to CausaGanha! This project scrapes legal gazette ZIPs from 91 Brazilian courts daily and uploads them to Internet Archive. We welcome contributions to help improve transparency in the Brazilian legal system.

This document outlines the constraints and requirements for contributing to the project, especially regarding adding new tribunals, data pipeline, and Internet Archive uploads.

## 1. Getting Started

Before you begin, ensure you have the following prerequisites installed:
- Python 3.12+
- `uv` (fast Python package installer and resolver)
- `git`

### Clone and setup:
```bash
git clone https://github.com/franklinbaldo/causaganha.git
cd causaganha
uv sync --dev
```

### Run tests:
```bash
uv run pytest
```

### Run linting and formatting:
```bash
uv run ruff check .
uv run ruff format .
```

## 2. Project Structure

A brief overview of key directories in the repository:

- `src/causaganha/`: Main Python package containing CLI, data pipeline, storage, and models.
- `src/causaganha/pipeline/`: Data collection, analysis, and orchestration logic.
- `djen-scraper/`: DJEN scraping infrastructure and conversion scripts.
- `dashboard/`: Pipeline monitoring dashboard (Astro/React).
- `tests/`: Unit and BDD tests.
- `.github/workflows/`: GitHub Actions pipelines for daily collection, catalog updates, and deployment.

## 3. How to Add a New Tribunal

We are continually expanding coverage to include all Brazilian courts. To add a new tribunal scraper:

1. **Find the gazette URL**: Usually formatted as `diariooficial.tjXX.jus.br` or similar, depending on the state/court.
2. **Look at an existing scraper for reference**: Explore `src/causaganha/pipeline/collect.py` and other files in `src/causaganha/pipeline/` or `djen-scraper/` to see how existing collections work.
3. **Create the scraper**: Follow the existing patterns to write a scraper that downloads the legal gazette and extracts the data.
4. **Add to the list of courts**: Update the `TRIBUNAIS` configuration list in `src/causaganha/config.py` with the new tribunal's exact DJEN code/sigla.
5. **Write tests**: Ensure your new scraper is fully tested (unit tests, mock responses). Tests are required for new scrapers.
6. **Open a PR**: Submit your pull request for review.

## 4. PR Checklist

Before submitting your PR, please verify the following:

- [ ] Tests added/updated (Tests are required for new scrapers)
- [ ] `ruff check` passes
- [ ] `ruff format` applied
- [ ] PR description explains the change (use "Refs #N" or "Closes #N" to link issues)

## 5. Code Style

- **Python**: We strictly use `ruff` for both linting and formatting. Ensure you run `uv run ruff check .` and `uv run ruff format .` before committing.
- **Type Hints**: Type hints are strongly encouraged for all Python code to ensure clarity and reliability.
- **Tests**: Tests are strictly required for any new scrapers, features, or bug fixes.

---

## Internet Archive (IA) Upload Constraints

**CRITICAL: Do not replace `httpx` with `boto3` for Internet Archive uploads.**

Our data pipeline uses the Internet Archive S3-compatible API. While it looks like standard S3, it has specific requirements that are incompatible with the default behavior of `boto3`:

1.  **Metadata Headers**: IA requires metadata headers to be prefixed with `x-archive-meta-*`. `boto3` hardcodes these to `x-amz-meta-*`, which IA ignores or rejects.
2.  **HTTP 411 Errors**: `boto3` often fails to set `Content-Length` correctly for IA's frontend, resulting in `HTTP 411 (Length Required)` errors.
3.  **History**: We have attempted to migrate to `boto3` twice, and both times it broke the pipeline (see PR #348).

Always use `httpx` or a direct HTTP client for IA interactions. For more details, refer to [Internet Archive Upload Architecture](docs/architecture/internet-archive-upload.md).

## Testing Requirements

Before merging any changes that affect the upload logic:

1.  **Local Verification**: Run the collection script locally with your IA credentials:
    ```bash
    export IAS3_ACCESS_KEY="your_key"
    export IAS3_SECRET_KEY="your_secret"
    python scripts/pipeline/collect.py --max-items 1 --date 2026-01-01 --tribunal STF
    ```
2.  **Verify Metadata**: Check the IA item metadata after upload to ensure all `x-archive-meta-*` headers are correctly processed by IA.
3.  **No Regressions**: Ensure that the `Content-MD5` check still passes and that retries are handled gracefully.

## Development Workflow

1.  Fork the repository.
2.  Create a feature branch.
3.  Ensure code follows `ruff` linting rules.
4.  Submit a Pull Request with a clear description of the changes.

## Security

Do not commit any credentials (`ia.ini`, `.env`, or hardcoded keys). Use environment variables for local testing.
