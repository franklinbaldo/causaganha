---
type: "RunGoal"
id: "run-goals/20260914t182457z-do-the-best-useful-work-availab/goal-real-archive-readback"
run: "runs/20260914T182457Z-do-the-best-useful-work-available-in-this-reposi"
kind: "task-advance"
goal: "Produce a real (not simulated) Internet Archive read-back proof for the currently published djen-tjro-2026/comunicacoes.parquet, and determine whether archive.org's endpoints actually support the CORS behavior DuckDBExplorer.svelte's browser-side read_parquet() depends on."
rationale: "handoffs/handoff-issue-1471-archive-readback names a real-Archive read-back proof (distinguishing genuine Archive delivery -- CORS, Range support, propagation -- from PR #1480's local-http-range-server-simulation) as the next concrete step for issue #1471/#1472, and no environment credential exists here to publish the candidate file first, so this round scopes to the achievable half: proving real read-back against the file already public today."
success_signal: "A JSON evidence file (docs/planning/evidence/pilot-tjro-2026-real-archive-readback.json) records real HTTP status/duration/bytes/CORS-header presence for archive.org's metadata and file-download endpoints, verifies Parquet magic bytes head+tail over a real Range request, and records real native-DuckDB cold/warm query timings against the live URL; new unit tests for the injectable probe/classification logic pass; full repo suite and ruff stay green."
status: "achieved"
---

# RunGoal
