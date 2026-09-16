---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-0iuk22-evidence-green-test"
run_id: "2026-09-16-exciting-mccarthy-0iuk22"
goal_id: "2026-09-16-exciting-mccarthy-0iuk22-goal-djen-sample-corpus-growth"
kind: "test_green"
reference: "tests/segmenter_dataset/test_ingest_djen_sample_technique1_batch.py, tests/segmenter_dataset/ (full dir)"
summary: "After fixing the fixtures: uv run pytest tests/segmenter_dataset/test_ingest_djen_sample_technique1_batch.py -q -> 6/6 passed (tribunal/document_type mapping for Sentenca and Acordao, unsupported tipoDocumento skip, verbatim-fidelity-mismatch skip, unmatched-candidate skip, _build_annotation contract). Full uv run pytest tests/segmenter_dataset -q -> all 372 tests passed, no regression in the existing suite (up from 365 recorded by the previous round + this round's 6 new + 1 extra pre-existing). ruff check and ruff format --check both pass on the new script and test file."
---

# Evidencia: GREEN apos a correcao dos fixtures

```
tests/segmenter_dataset/test_ingest_djen_sample_technique1_batch.py ...... [100%]
```

```
uv run pytest tests/segmenter_dataset -q
................................................................ (372 passed)
```

`uv run ruff check` e `uv run ruff format --check` limpos nos dois arquivos
novos.
