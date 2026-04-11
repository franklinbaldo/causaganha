# Contributing to CausaGanha

This project is under active refactoring. Contributions are welcome, but changes need to stay aligned with the current codebase, CI, and operational constraints.

## Development setup

Requirements:

- Python 3.12+
- `uv`
- `git`
- Node.js and `npm` for web development

Setup:

```bash
git clone https://github.com/franklinbaldo/causaganha.git
cd causaganha
uv sync --dev
cp .env.example .env
uv run pre-commit install
```

## Core commands

Python quality checks:

```bash
uv run pytest -q
uv run ruff format --check
uv run ruff check
uvx vulture src/ scripts/ vulture_whitelist.py --min-confidence 100
```

Frontend checks:

```bash
cd web
npm ci
npm run lint
npm test
npm run build
```

## Repository map

- [src/causaganha](/Users/frank/workspace/causaganha/src/causaganha): main Python package
- [src/djen_backup](/Users/frank/workspace/causaganha/src/djen_backup): ZIP and backfill utilities
- [web](/Users/frank/workspace/causaganha/web): Astro + Svelte frontend
- [scripts](/Users/frank/workspace/causaganha/scripts): operational scripts and pipeline helpers
- [tests](/Users/frank/workspace/causaganha/tests): pytest and pytest-bdd suites
- [.github/workflows](/Users/frank/workspace/causaganha/.github/workflows): CI and production workflows

## Contribution rules

- Keep docs in sync with the code you change.
- Do not introduce undocumented operational behavior.
- Prefer narrow PRs over large mixed changes.
- Add or update tests when behavior changes.
- Avoid reviving legacy paths or directories unless the repository still uses them.

## Internet Archive rule

Do not replace Internet Archive upload logic with `boto3`.

Reason:

- IA metadata handling depends on custom headers that are not a clean fit for standard AWS S3 client behavior.
- The project explicitly treats `httpx`-based upload code as the supported path for IA uploads.
- `boto3` in this repository is only for cold-storage use cases, not DJEN archival uploads.

If your change touches archival code, validate the affected path carefully.

## DJEN access rule

DJEN direct access is the default for local runs in Brazil. Use the Cloud Run proxy only when `--use-proxy` or `DJEN_USE_PROXY=1` is explicitly set, such as in GitHub Actions. Do not hardcode environment-specific URLs into application logic.

## Pull requests

Before opening a PR:

- make sure `ruff format --check` passes
- make sure `ruff check` passes
- make sure tests relevant to your change pass
- make sure the frontend builds if you touched `web/`
- update docs when commands, architecture, or behavior changed

Recommended PR checklist:

- [ ] scope is clear and limited
- [ ] tests added or updated when needed
- [ ] docs updated when needed
- [ ] no credentials or environment secrets committed
- [ ] CI passes

## Adding or changing pipeline behavior

If you change collection, consolidation, catalog, or deployment behavior:

- inspect the corresponding workflow in [.github/workflows](/Users/frank/workspace/causaganha/.github/workflows)
- verify the script or CLI entrypoint it invokes still matches
- update root docs if operator-facing behavior changes

## Security

- Never commit `.env`, IA credentials, or service tokens.
- Prefer environment variables for all secrets.
- Treat Internet Archive item naming and metadata as part of the public contract.
