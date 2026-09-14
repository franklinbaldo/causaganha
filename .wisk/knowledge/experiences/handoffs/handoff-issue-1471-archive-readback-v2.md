---
type: "Handoff"
id: "handoffs/handoff-issue-1471-archive-readback-v2"
title: "Finish issue #1471's TJRO 2026 pilot: publish candidate to Internet Archive, real candidate read-back proof, advance/revise/hold decision"
created_at: "2026-09-14T18:45:21.968697Z"
status: "active"
created_by_run: "runs/20260914T182457Z-do-the-best-useful-work-available-in-this-reposi"
state: "This round produced a real (non-simulated) Internet Archive read-back proof for the currently published djen-tjro-2026/comunicacoes.parquet only (docs/planning/evidence/pilot-tjro-2026-real-archive-readback.json, scripts/benchmarks/pilot_tjro_2026_real_archive_readback.py): metadata/head-range/tail-range probes all real, Parquet magic bytes verified at both ends of a real Range response, native DuckDB cold/warm query timing against the live URL. It could not publish the candidate (reordered) file -- no IA_ACCESS_KEY/IA_SECRET_KEY present in this environment -- so no apples-to-apples real read-back against the candidate exists yet. It also found and filed, as its own issue (#1482) rather than folding into this decision, that archive.org's file-download endpoint sends no Access-Control-Allow-Origin header (unlike its metadata/advancedsearch endpoints) -- confirmed with two independent HTTP clients against three real endpoints, but not yet confirmed in a real browser (scripts/benchmarks/archive_cors_probe.mjs was written but blocked in this sandbox by a Playwright/Chromium TLS-trust gap with this session's own forced MITM egress proxy, an environment limitation unrelated to archive.org)."
next_action: "Once IA write credentials are available: (1) publish the candidate comunicacoes.parquet as a pilot to djen-tjro-2026, preserving rollback (keep the currently published file recoverable, do not delete/overwrite without a documented way back); (2) run scripts/benchmarks/pilot_tjro_2026_real_archive_readback.py's technique (or a small extension of it) against the newly published candidate for a true apples-to-apples real-Archive comparison against this round's old-file baseline numbers; (3) separately, run scripts/benchmarks/archive_cors_probe.mjs (or a small CI job) in an environment with normal internet access -- no forced TLS-intercepting proxy -- to get a definitive real-browser confirmation of issue #1482's CORS finding, since it may already affect the live DuckDBExplorer feature today regardless of the reorder decision; (4) only after the candidate's real read-back is validated, record issue #1471's advance/revise/hold decision with agreed regression limits, using PR #1480's local-simulation numbers and this round's real old-file numbers together as the baseline -- do not promote catalog/certification before that read-back is validated, per the issue's own text."
references: ["https://github.com/franklinbaldo/causaganha/issues/1471", "https://github.com/franklinbaldo/causaganha/issues/1472", "https://github.com/franklinbaldo/causaganha/issues/1482", "https://github.com/franklinbaldo/causaganha/pull/1480"]
goals: ["run-goals/20260914t182457z-do-the-best-useful-work-availab/goal-real-archive-readback"]
repository_head: "0acf72ae7e47e205d6b253f7b6b28bc65b96331d"
repository_branch: "claude/exciting-mccarthy-9w2u6q"
repository_dirty: true
repository_diff_digest: "sha256:128f67a280455dc5dc5723f75ebdde417cba235f3044dbb54c123877692b1910"
target_session_type: "session-types/standard-experience"
---

# Handoff
