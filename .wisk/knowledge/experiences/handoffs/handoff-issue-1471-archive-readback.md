---
type: "Handoff"
id: "handoffs/handoff-issue-1471-archive-readback"
title: "Finish issue #1471's TJRO 2026 pilot: Internet Archive publish + read-back proof + advance/revise/hold decision"
created_at: "2026-09-14T18:18:13.363122Z"
status: "active"
created_by_run: "runs/20260914T172602Z-do-the-best-useful-work-available-in-this-reposi"
state: "PR #1480 (pending merge) completed the DuckDB native+WASM query-cost measurement: a date-only COUNT(*) touches 2/9 row groups in the currently published djen-tjro-2026/comunicacoes.parquet vs 9/9 in the numero_processo-first candidate rewrite, 4 vs 11 HTTP requests cold, ~8x more warm-cache bytes/iteration -- all measured via a new local Range-serving HTTP server (scripts/benchmarks/pilot_tjro_2026_query_cost.py), explicitly labeled 'local-http-range-server-simulation' since it is NOT a real-Archive read-back proof. handoffs/handoff-issue-1471-perf-and-readback (superseding handoffs/handoff-issue-1471-pilot-validation) is archived by this handoff."
next_action: "Once PR #1480 is merged: (1) publish the candidate comunicacoes.parquet as a pilot to djen-tjro-2026 on Internet Archive, preserving rollback (keep the currently published file recoverable -- do not delete/overwrite without a documented way back); (2) do a controlled read-back proof against the real archive.org host, distinguishing genuine Archive delivery (CORS behavior, Range support, propagation delay after upload) from the local-server simulation already done -- scripts/benchmarks/pilot_tjro_2026_query_cost.py's serve_directory()/_RequestStats request-and-byte-accounting technique can be pointed at real archive.org responses for an apples-to-apples comparison against this round's local numbers, and its wasm_query_bench.mjs Playwright harness already handles the httpfs-extension/proxy/bare-specifier issues documented in wiki/continuous-loop-operational-invariants.md for reuse against the real host; (3) only after that read-back is validated, record issue #1471's advance/revise/hold decision with agreed regression limits from PR #1480's numbers as the baseline -- do not promote catalog/certification before read-back is validated, per the issue's own text."
references: ["[\"https://github.com/franklinbaldo/causaganha/issues/1471\", \"https://github.com/franklinbaldo/causaganha/pull/1480\", \"https://github.com/franklinbaldo/causaganha/pull/1478\"]"]
goals: []
repository_head: "624becc63d0cfec75b5bdc5271b8255070b2b660"
repository_branch: "claude/exciting-mccarthy-dfmmxd"
repository_dirty: true
repository_diff_digest: "sha256:49771ecfe6bfcc4176f82153f2b96e4a12e8d2c079e7885b069b99c9beefc160"
target_session_type: "session-types/standard-experience"
---

# Handoff
