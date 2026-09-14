---
created_at: "2026-09-14T18:18:13.363122Z"
created_by_run: "runs/20260914T172602Z-do-the-best-useful-work-available-in-this-reposi"
goals: []
id: "handoffs/handoff-issue-1471-archive-readback"
next_action: "Once PR #1480 is merged: (1) publish the candidate comunicacoes.parquet as a pilot to djen-tjro-2026 on Internet Archive, preserving rollback (keep the currently published file recoverable -- do not delete/overwrite without a documented way back); (2) do a controlled read-back proof against the real archive.org host, distinguishing genuine Archive delivery (CORS behavior, Range support, propagation delay after upload) from the local-server simulation already done -- scripts/benchmarks/pilot_tjro_2026_query_cost.py's serve_directory()/_RequestStats request-and-byte-accounting technique can be pointed at real archive.org responses for an apples-to-apples comparison against this round's local numbers, and its wasm_query_bench.mjs Playwright harness already handles the httpfs-extension/proxy/bare-specifier issues documented in wiki/continuous-loop-operational-invariants.md for reuse against the real host; (3) only after that read-back is validated, record issue #1471's advance/revise/hold decision with agreed regression limits from PR #1480's numbers as the baseline -- do not promote catalog/certification before read-back is validated, per the issue's own text."
references: ["[\"https://github.com/franklinbaldo/causaganha/issues/1471\", \"https://github.com/franklinbaldo/causaganha/pull/1480\", \"https://github.com/franklinbaldo/causaganha/pull/1478\"]"]
repository_branch: "claude/exciting-mccarthy-dfmmxd"
repository_diff_digest: "sha256:49771ecfe6bfcc4176f82153f2b96e4a12e8d2c079e7885b069b99c9beefc160"
repository_dirty: "true"
repository_head: "624becc63d0cfec75b5bdc5271b8255070b2b660"
state: "PR #1480 (pending merge) completed the DuckDB native+WASM query-cost measurement: a date-only COUNT(*) touches 2/9 row groups in the currently published djen-tjro-2026/comunicacoes.parquet vs 9/9 in the numero_processo-first candidate rewrite, 4 vs 11 HTTP requests cold, ~8x more warm-cache bytes/iteration -- all measured via a new local Range-serving HTTP server (scripts/benchmarks/pilot_tjro_2026_query_cost.py), explicitly labeled 'local-http-range-server-simulation' since it is NOT a real-Archive read-back proof. handoffs/handoff-issue-1471-perf-and-readback (superseding handoffs/handoff-issue-1471-pilot-validation) is archived by this handoff."
status: "archived"
target_session_type: "session-types/standard-experience"
title: "Finish issue #1471's TJRO 2026 pilot: Internet Archive publish + read-back proof + advance/revise/hold decision"
type: "Handoff"
continued_by_run: "runs/20260914T182457Z-do-the-best-useful-work-available-in-this-reposi"
archived_at: "2026-09-14T18:44:54.827871Z"
resolution: "Completed the achievable slice: a real (non-simulated) Internet Archive read-back proof for the currently published djen-tjro-2026/comunicacoes.parquet -- metadata/head-range/tail-range probes, Parquet magic-byte verification, and native-DuckDB cold/warm query timing, all against the live archive.org host (docs/planning/evidence/pilot-tjro-2026-real-archive-readback.json). Publishing the candidate (reordered) file itself is still blocked: no IA_ACCESS_KEY/IA_SECRET_KEY in this environment, and a live production IA write is a hard-to-reverse, shared-system action appropriately left to a session that has those credentials. An independent, real finding from this round's probing -- archive.org's file-download endpoint sends no Access-Control-Allow-Origin header, unlike its metadata/advancedsearch endpoints, which DuckDBExplorer.svelte's browser-side read_parquet() may depend on -- was filed as issue #1482 rather than folded into this decision, since it affects the currently published file regardless of the reorder pilot. Superseded by handoffs/handoff-issue-1471-archive-readback-v2 for the remaining publish+candidate-read-back+decision scope."
---

# Handoff
