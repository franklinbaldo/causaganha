---
type: AgentCheck
id: "2026-09-20-exciting-mccarthy-fv62kx-check-ruff-pytest-batch24"
run_id: "2026-09-20-exciting-mccarthy-fv62kx"
command: "uv run ruff check; uv run ruff format --check; uv run pytest -q tests/segmenter_dataset; scripts/segmenter_semantic_audit.py"
result: "passed"
evidence_id: "2026-09-20-exciting-mccarthy-fv62kx-evidence-batch24-ingested"
summary: "ruff check: All checks passed. ruff format --check: 454 files already formatted. pytest tests/segmenter_dataset: 208 passed, 0 failed. semantic audit: 11 findings, all in pre-existing doc_ids, zero overlap with the 6 new batch24 doc_ids."
---

# Check: lint, testes e auditoria semântica (batch24)

- `uv run ruff check` → "All checks passed!"
- `uv run ruff format --check` → "454 files already formatted"
- `uv run pytest -q tests/segmenter_dataset` → 208 passed (100%), 0 failed
- `scripts/segmenter_semantic_audit.py` → 11 achados totais, todos com
  `doc_id` pré-existente (confirmado por comparação programática de
  conjuntos contra os 6 `doc_id`s deste lote: interseção vazia)
