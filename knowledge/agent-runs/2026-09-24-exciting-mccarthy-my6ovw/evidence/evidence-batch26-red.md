---
type: AgentEvidence
id: "2026-09-24-exciting-mccarthy-my6ovw-evidence-batch26-red"
run_id: "2026-09-24-exciting-mccarthy-my6ovw"
goal_id: "2026-09-24-exciting-mccarthy-my6ovw-goal-djen-sample-batch26"
kind: "test_red"
reference: "tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch26_corpus_growth"
summary: "Added test_real_store_reflects_batch26_corpus_growth asserting document_count>=193 and presence of TJCE/363694252 (hash 797cacef...) and TJSC/587254831 (hash 6a5fa9ef... at this point, computed from the raw HTML-wrapped candidate text) document hashes. Ran uv run pytest tests/segmenter_dataset/test_segmenter_governance_status.py::test_real_store_reflects_batch26_corpus_growth -q: FAILED, AssertionError: assert 191 >= 193 -- confirms RED against the current store (191 documents, post-#1598-merge) before ingestion. The TJSC hash was later recomputed to 4f966854... after decision-clean-tjsc-html.md's HTML-to-text cleanup and the test updated accordingly -- see evidence-batch26-ingested for the final, GREEN state."
---

# Evidência: RED do lote 26
