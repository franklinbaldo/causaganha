---
type: "RunCheck"
id: "run-checks/20260926t012508z-do-the-best-useful-work-availab/check-verification-tjpa-review"
run: "runs/20260926T012508Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run python scripts/segmenter_governance_status.py --store data/segmenter (before/after); uv run pytest -q tests/segmenter_dataset; uv run python scripts/segmenter_semantic_audit.py; uv run ruff check; uv run ruff format --check"
result: "review_count 31->32, test_count 2->3 (val_count unchanged at 29, both below the 29/29 ceiling itself below RFC 0012's 30/30 floor -- corpus-scale-blocked, tracked separately by issue #1050). tests/segmenter_dataset: 251 passed. Semantic audit: no new findings (6 pre-existing _collapsed docs unchanged, this doc not among them). ruff check/format --check: clean, 462 files. A second candidate document (doc_82d8ee7168b24d787ce0417f888d1eb3, TJPB) was attempted twice via independent haiku-family second annotations but both failed mechanical/verbatim verification before ingestion (never written to the store): attempt 1 silently dropped a real clause ('DEFIRO...REVOGO...' from a long multi-clause dispositivo sentence) and normalized curly quotes to straight; attempt 2 fixed the dropped clause and quote issue was not fully fixed either (still emitted straight quotes instead of the source's curly “a”) and introduced new mechanical defects (5x duplicate single-anchor 'resultado' tags -- one per verb clause, violating the guideline's single-operative-mention rule -- plus an overlapping fundamentacao_legal span and an undeclared unmatched relatorio pair). Neither was ingested; this document remains single-annotated and untouched in the store."
status: "pass"
goal: "run-goals/20260926t012508z-do-the-best-useful-work-availab/goal-segmenter-adjudication-slice"
---

# RunCheck
