---
type: AgentGoal
id: "2026-09-05-exciting-mccarthy-fnt3vx-goal-purge-dead-experiment-imports"
run_id: "2026-09-05-exciting-mccarthy-fnt3vx"
goal: "Remove experiments/archive/test_all_improvements.py and experiments/archive/test_djen_api.py: both import modules genuinely deleted from the codebase (causaganha.analysis.embedding_service_v2, causaganha.analysis.embedding_models, causaganha.pipeline.embedding_pipeline, causaganha.storage.embedding_storage, causaganha.api.client) and cannot execute."
rationale: "Issue #924 (3.3, 'purgar restos mortais') claimed these files were dead; most of its other dead-code claims (scripts/db/, deployment/cron, deployment/systemd, notebooks/train_privacy_filter.*, AUDIT.md) were already removed by earlier work, but these two files survived and were never verified live until this round. Confirmed via `uv run python3 -c 'import <module>'`: 5 of 6 imports across the two files raise ModuleNotFoundError. CLAUDE.md's project-wide instruction is explicit — files referencing removed infrastructure mislead contributors and agents; if something is confirmed unused/broken, delete it completely rather than leave it as misleading pseudo-documentation. This is a small, self-contained, non-web slice that does not touch any file the two concurrent open PRs (#1160/#1161) or the segmenter roadmap depend on."
success_signal: "Both files are deleted. Nothing in the repo (workflows, docs, ruff.toml's extend-exclude, other scripts/tests) references either filename after deletion (grep clean). `uv run ruff check`, `uv run ruff format --check`, and the full `uv run pytest -q` suite stay green (these two files were never collected by pytest — testpaths=[\"tests\"] excludes experiments/ — so their removal is expected to be a no-op for suite results, proving the deletion is safe rather than a regression)."
status: "achieved"
---

# Goal: remover módulos de teste órfãos em experiments/archive/

Fecha, com verificação ao vivo (não apenas leitura da issue), a única alegação de "código morto" da #924 que ainda não tinha sido corrigida por rodadas anteriores.
