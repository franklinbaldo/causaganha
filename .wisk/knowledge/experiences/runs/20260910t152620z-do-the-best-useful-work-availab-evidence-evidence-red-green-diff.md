---
type: "RunEvidence"
id: "run-evidence/20260910t152620z-do-the-best-useful-work-availab/evidence-red-green-diff"
run: "runs/20260910T152620Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/test_except_exception_policy.py"
summary: "RED: extended test_except_exception_policy.py with two new tests -- test_confirmed_scripts_bulkheads_cite_the_bulkhead_adr (adds scripts/pipeline/embed_v2.py to _SCRIPTS_CHECKED) and test_append_manifest_narrows_except_exception_to_specific_types (new _SCRIPTS_NARROWED set for scripts/append_manifest.py) -- both failed against unmodified source (embed_v2.py:238 missing ADR citation; append_manifest.py:56,100 bare except Exception). GREEN after two source fixes: (1) scripts/pipeline/embed_v2.py's upload_embeddings_to_ia per-date/tribunal IA-upload bulkhead (called in a loop over all dates in main(), already calling logger.exception before returning a False sentinel) got the trailing '# per-date/tribunal upload bulkhead, see docs/adr/0011' comment on the except line, matching annotate_with_llm.py's existing citation style. (2) scripts/append_manifest.py's two sites -- download_existing_manifest (single fallback-URL fetch+JSON-parse, not a worker-pool loop) and get_new_uploads (single CSV read+parse) -- were narrowed from 'except Exception' to '(OSError, json.JSONDecodeError, UnicodeDecodeError)' and '(OSError, csv.Error, UnicodeDecodeError)' respectively, since urllib.error.URLError is already caught separately and is itself an OSError subclass. uv run pytest tests/test_except_exception_policy.py -v: 3 passed. uv run ruff check . and uv run ruff format --check . both pass repo-wide."
goal: "run-goals/20260910t152620z-do-the-best-useful-work-availab/goal-adr0011-append-manifest-embed-v2"
---

# RunEvidence
