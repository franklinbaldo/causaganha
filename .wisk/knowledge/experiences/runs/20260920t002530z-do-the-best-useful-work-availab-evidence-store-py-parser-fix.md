---
type: "RunEvidence"
id: "run-evidence/20260920t002530z-do-the-best-useful-work-availab/store-py-parser-fix"
run: "runs/20260920T002530Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "https://github.com/franklinbaldo/causaganha/pull/1588 commit 967eebc; uv run pytest -q tests/segmenter_dataset/test_store.py (RED antes, GREEN depois); uv run pytest -q tests/segmenter_dataset (suite completa, 173 docs, exit 0); uv run ruff check/format --check limpos"
summary: "Corrigido segmenter_dataset.store._text_element_to_labels: o ramo _PAIR_ROLES descartava silenciosamente labels singleton aninhados dentro do proprio papel inicio/fim (classe de risco 17, documentada mas nao corrigida pela PR #1586). Novo teste RED (test_singleton_label_nested_inside_pair_role_survives_round_trip) reproduziu a perda (2 de 3 labels recuperados); fix faz o ramo tambem splicar child_items, espelhando o ramo elif vizinho. Suite completa tests/segmenter_dataset (173 documentos reais) verde apos o fix."
goal: "goal-batch23-merge-and-batch24"
decision: "decision-substitute-batch24-with-parser-fix"
---

# RunEvidence
