---
type: "RunReading"
id: "run-readings/20260914t193005z-do-the-best-useful-work-availab/reading-active-handoffs"
run: "runs/20260914T193005Z-do-the-best-useful-work-available-in-this-reposi"
kind: "active-handoffs"
subject: "Active Wisk handoffs (wisk handoff list)"
reference: ".wisk/knowledge/experiences/handoffs/handoff-issue-1471-archive-readback.md"
finding: "Only one active handoff: handoff-issue-1471-archive-readback (v1), target session-types/standard-experience, baseline branch claude/exciting-mccarthy-dfmmxd@624becc marked dirty=true. It predates PR #1480 (merged, query-cost measurement) and PR #1483 (open on main, CI green, mergeable clean), which already delivered a real non-simulated archive.org read-back proof for the currently-published djen-tjro-2026 parquet, could not publish the reordered candidate (no IA_ACCESS_KEY/IA_SECRET_KEY in that session either), and filed independent issue #1482 (archive.org's /download endpoint sends no CORS header, which can break DuckDBExplorer.svelte's browser-side read_parquet today, unrelated to the reorder pilot). PR #1483 intends to archive this handoff and create a v2 successor once merged, but main does not have that yet."
---

# RunReading
