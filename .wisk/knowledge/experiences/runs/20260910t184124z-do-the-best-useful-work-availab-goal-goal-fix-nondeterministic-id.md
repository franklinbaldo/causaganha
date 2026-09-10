---
goal: "Fix scripts/bootstrap_training_corpus.py's load_texts(): its fallback text id (used when a source record has no explicit 'id'/'text_uuid') is str(hash(texto[:200])), which is non-deterministic across process runs due to Python's string-hash randomization (PYTHONHASHSEED), unlike the sibling script augment_segmenter_data.py's deterministic uuid5-based id for the same need. Replace with a stable hash and add a test."
id: "run-goals/20260910t184124z-do-the-best-useful-work-availab/goal-fix-nondeterministic-id"
kind: "task-advance"
rationale: "Reading scripts/bootstrap_training_corpus.py end-to-end (the long-tail defect audit named by PR #1408's next_move) found both call sites of the id fallback (JSONL and parquet branches) use Python's hash() builtin. Empirically confirmed hash() differs across separate process runs for the same string (verified with 3 separate  invocations printing different hash values for the same literal). Since this pipeline's own two-stage design (--save-intermediate writes ids to an intermediate file for Stage 2 to later cross-reference, per the file's own docstring) implies ids should identify 'the same text' consistently, a fallback id that silently changes every run breaks that expectation for any input lacking an explicit id."
run: "runs/20260910T184124Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "A failing test demonstrates the fallback id is not the deterministic value it should be (compared against a hand-computed stable hash) against the unmodified code; after switching to hashlib.sha256, the same test passes; full ruff+pytest green; PR opened."
type: "RunGoal"
---

# RunGoal
