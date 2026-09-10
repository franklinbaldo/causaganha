---
type: "RunEvidence"
id: "run-evidence/20260910t180632z-do-the-best-useful-work-availab/evidence-three-files-clean"
run: "runs/20260910T180632Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "scripts/classify_from_batch_embeddings.py, scripts/analyze_with_rag.py, scripts/stress_test_djen.py"
summary: "Read all three end-to-end. classify_from_batch_embeddings.py: already narrows its except-Exception (duckdb.Error, KeyError, ValueError, TypeError); has one genuinely dead helper (cosine_similarity, defined but never called since the file uses LanceDB's own built-in vector search instead) but this is unused-code cleanup, not a behavioral defect, so left alone rather than forced into a fix; no wrong-value bug found. analyze_with_rag.py: a near-duplicate of classify_from_batch_embeddings.py per its own RFC docstring comment (overlaps -- which is the keeper?); same structure, same already-narrowed exception handling, no defect found. stress_test_djen.py: a DJEN rate-limit diagnostic tool; verified its error classification correctly treats 403/timeout/5xx/err: as errors while correctly excluding 404 (genuine absence) and never conflating 403 with absence (matches CLAUDE.md's 'never treat 403 as absent' -- here 403 is legitimately counted as a rate-limit signal, a different concern from availability); verified the geometric concurrency-level progression and business_days helper are both correct; no defect found. All three: clean, no code change."
goal: "run-goals/20260910t180632z-do-the-best-useful-work-availab/goal-audit-three-more-longtail-files"
---

# RunEvidence
