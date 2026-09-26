---
type: AgentCheck
id: "2026-09-26-exciting-mccarthy-ku8qje-check-semantic-audit-ruff"
run_id: "2026-09-26-exciting-mccarthy-ku8qje"
goal_id: "2026-09-26-exciting-mccarthy-ku8qje-goal-segmenter-batch28"
command: "uv run python scripts/segmenter_semantic_audit.py; uv run pytest -q tests/segmenter_dataset; uv run ruff check; uv run ruff format --check"
result: "passed"
evidence_id: "2026-09-26-exciting-mccarthy-ku8qje-evidence-batch28-ingested"
summary: "`segmenter_semantic_audit.py`: exatamente os 7 doc_ids `_collapsed` já na allowlist de `tests/segmenter_dataset/test_segmenter_audit_scripts.py`, nenhum dos dois documentos novos aparece em qualquer achado. `pytest -q tests/segmenter_dataset`: 253 passed (após a atualização do guard de teto em decision-update-stale-guard). `ruff check`: All checks passed. `ruff format --check`: 462 files already formatted."
---

# Check: audit semântico, suíte segmenter_dataset e ruff
