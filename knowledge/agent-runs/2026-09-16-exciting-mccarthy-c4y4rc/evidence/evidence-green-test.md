---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-c4y4rc-evidence-green-test"
run_id: "2026-09-16-exciting-mccarthy-c4y4rc"
kind: "test_green"
reference: "scripts/segmenter_governance_status.py, tests/segmenter_dataset/test_segmenter_governance_status.py"
summary: "Apos implementar val_count/test_count (via assign_splits real) e val_ceiling_at_full_adjudication/test_ceiling_at_full_adjudication (via assign_splits simulando evaluation_eligible=train_eligible inteiro) mais meets_rfc_0012_split_floor/corpus_scale_blocks_floor, os 5 testes do arquivo passam (uv run pytest tests/segmenter_dataset/test_segmenter_governance_status.py -q). Suite completa tests/segmenter_dataset: 365/365 verde. ruff check/format limpos nos 2 arquivos tocados."
---

# Evidencia: GREEN apos a mudanca

```
uv run pytest tests/segmenter_dataset/test_segmenter_governance_status.py -q
.....                                                                    [100%]

uv run pytest tests/segmenter_dataset -q
........................................................................ [ 19%]
........................................................................ [ 39%]
........................................................................ [ 59%]
........................................................................ [ 78%]
........................................................................ [ 98%]
......                                                                   [100%]

uv run ruff check scripts/segmenter_governance_status.py tests/segmenter_dataset/test_segmenter_governance_status.py
All checks passed!
uv run ruff format --check scripts/segmenter_governance_status.py tests/segmenter_dataset/test_segmenter_governance_status.py
2 files already formatted
```
