---
created_at: "2026-09-14T15:41:35.304262Z"
created_by_run: "runs/20260914T152436Z-do-the-best-useful-work-available-in-this-reposi"
goals: []
id: "handoffs/handoff-issue-1471-perf-and-readback"
next_action: "Once PR #1478 is merged: (1) measure date-only query cost under the new ordering using both DuckDB native and DuckDB-WASM, separating engine init / cold query / warm cache, recording bytes/requests/duration/sample/environment -- compare against the pre-reorder file's own cost, not an assumption; (2) publish the candidate comunicacoes.parquet as a pilot to djen-tjro-2026 on Internet Archive preserving rollback (keep the current file recoverable), then do a controlled read-back proof distinguishing real Archive delivery (CORS/Range/propagation) from a local simulation; (3) only after that read-back is validated, record the advance/revise/hold decision with agreed regression limits per the issue's acceptance criteria. Do not promote catalog/certification before read-back is validated."
references: ["[\"https://github.com/franklinbaldo/causaganha/issues/1471\", \"https://github.com/franklinbaldo/causaganha/pull/1478\", \"https://github.com/franklinbaldo/causaganha/issues/1470\"]"]
repository_branch: "claude/exciting-mccarthy-209hem"
repository_diff_digest: "sha256:1f2b62ef7c6034984319b7ff2cf3d4e744a136c51b44af4cac381f5dac2fbe60"
repository_dirty: "true"
repository_head: "729e9c08de0039373404f0d7453c83ad38d112bc"
state: "PR #1478 completed the local diff/verification slice of #1471 (row count, id set, CNJ normalization contract, other-fields-untouched, footer/compression contract, true physical sort order via file_row_number+lag(), spot-check CNJ -- all passed, docs/planning/evidence/pilot-tjro-2026-local-comparison.json) and posted results to the issue. handoffs/handoff-issue-1471-pilot-validation is superseded by this one."
status: "archived"
target_session_type: "session-types/standard-experience"
title: "Finish issue #1471's TJRO 2026 pilot: DuckDB perf measurement + Archive read-back proof"
type: "Handoff"
continued_by_run: "runs/20260914T172602Z-do-the-best-useful-work-available-in-this-reposi"
archived_at: "2026-09-14T18:17:56.324645Z"
resolution: "Completed the DuckDB native+WASM query-cost measurement half of this handoff's next_action (PR #1480): a date-only COUNT(*) touches 2/9 row groups in the old file vs 9/9 in the candidate, 4 vs 11 HTTP requests cold, ~8x more warm-cache bytes/iteration -- quantified via a new local Range-serving HTTP server (scripts/benchmarks/pilot_tjro_2026_query_cost.py) reused by both the native and a real-Chromium-via-Playwright WASM benchmark. The Archive publish/read-back proof and the resulting advance/revise/hold decision (parts 2-3 of this handoff's next_action) remain open and are carried forward in handoffs/handoff-issue-1471-archive-readback."
---

# Handoff
