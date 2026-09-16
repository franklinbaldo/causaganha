---
type: AgentGoal
id: "2026-09-16-exciting-mccarthy-hv2ep2-goal-batch9-corpus-growth"
run_id: "2026-09-16-exciting-mccarthy-hv2ep2"
goal: "Ingest a fresh batch of 5-8 real, previously-unused DJEN sample documents (Sentença/Acórdão) into the segmenter_dataset store via scripts/ingest_djen_sample_technique1_batch.py, growing document_count and the RFC 0012 Sec 5 item 4 val/test ceilings, without regressing any existing test or introducing a new unverified semantic-audit finding."
rationale: "RFC 0012 Sec 5 item 4's per-split floor (>=30 val, >=30 test, each adjudicated) is mathematically unreachable at the current corpus size (109 documents pre-round, val/test ceiling 16/16 per live scripts/segmenter_governance_status.py) -- proven and tested in round c4y4rc. Issue #1051 (adjudication) is correctly parked until #1050 (corpus growth) closes most of the gap. Eight prior batches already proved the ingestion path scales without production-code changes; this round continues that proof rather than re-deriving it."
success_signal: "scripts/segmenter_governance_status.py, run live against the real data/segmenter store, reports document_count and val_ceiling_at_full_adjudication/test_ceiling_at_full_adjudication strictly higher than the pre-round snapshot (109/16/16), with the new tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch8_corpus_growth guard passing GREEN, uv run pytest -q green on the full suite, ruff check/format clean, and evidence + a knowledge/backlog/issue-1050.md update landed alongside a PR."
status: "achieved"
---

# Goal: batch9 corpus growth for #1050

Meta única desta rodada: mais um lote real de ingestão via
`ingest_djen_sample_technique1_batch.py`, seguindo exatamente o mesmo
fluxo TDD das 8 rodadas anteriores, sem tocar em #1051 diretamente.
