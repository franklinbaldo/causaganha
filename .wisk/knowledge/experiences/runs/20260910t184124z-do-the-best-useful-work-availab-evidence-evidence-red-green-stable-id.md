---
type: "RunEvidence"
id: "run-evidence/20260910t184124z-do-the-best-useful-work-availab/evidence-red-green-stable-id"
run: "runs/20260910T184124Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/test_bootstrap_training_corpus.py"
summary: "scripts/bootstrap_training_corpus.py's load_texts() derived a fallback id (used when a source record has no explicit 'id'/'text_uuid') via str(hash(texto[:200])) at two call sites (JSONL and parquet branches). Confirmed empirically that Python's builtin hash() for strings is randomized per process (PYTHONHASHSEED, PEP 456) via three separate 'uv run python' invocations printing three different hash values for the identical literal string. This breaks the pipeline's own two-stage design (documented at the top of the file): --save-intermediate writes ids to an intermediate file specifically so Stage 2 can cross-reference records later, but a fallback id that silently changes every run defeats that for any input lacking an explicit id. The sibling script scripts/augment_segmenter_data.py, read earlier in this same audit, correctly uses a deterministic uuid5-based id for the identical need, making this an inconsistency within the same audit rather than a one-off. Extracted _stable_fallback_id(texto) using hashlib.sha256(texto[:200].encode()).hexdigest() and used it at both call sites. RED: 2 new tests in tests/test_bootstrap_training_corpus.py -- test_load_texts_jsonl_fallback_id_is_deterministic failed against the unmodified code (assert '2860603732365749551' == '67cd12f9c213...' -- the hash()-based id vs. the independently-computed sha256 hex digest the test expects). GREEN after the fix: 2/2 passed. ruff check clean; ruff format applied one reformat to the new test file (blank-line/wrap style), re-verified clean after. Full uv run pytest -q (entire suite) green."
goal: "run-goals/20260910t184124z-do-the-best-useful-work-availab/goal-fix-nondeterministic-id"
---

# RunEvidence
