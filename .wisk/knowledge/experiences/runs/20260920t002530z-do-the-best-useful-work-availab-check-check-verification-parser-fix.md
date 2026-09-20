---
type: "RunCheck"
id: "run-checks/20260920t002530z-do-the-best-useful-work-availab/check-verification-parser-fix"
run: "runs/20260920T002530Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q tests/segmenter_dataset/test_store.py::test_singleton_label_nested_inside_pair_role_survives_round_trip (RED antes do fix, GREEN depois); uv run pytest -q tests/segmenter_dataset (suite completa, 173 documentos reais); uv run ruff check src/segmenter_dataset/store.py tests/segmenter_dataset/test_store.py; uv run ruff format --check idem; pull_request_read get_check_runs em #1586 e #1588"
result: "RED confirmado (AssertionError: labels recuperados 2 de 3, resultado ausente). GREEN apos o fix (12 passed em test_store.py, era 11). Suite completa tests/segmenter_dataset: exit code 0, sem falhas. ruff check/format --check limpos nos dois arquivos tocados. PR #1586: 11/11 checks completed/success, mesclada. PR #1588: 9/10 checks completed/success (CodeQL/GitGuardian/lint/web/Analyze x4 verdes), tests (tjro) ainda em andamento no momento deste check."
status: "pass"
evidence: "store-py-parser-fix"
goal: "goal-batch23-merge-and-batch24"
---

# RunCheck
