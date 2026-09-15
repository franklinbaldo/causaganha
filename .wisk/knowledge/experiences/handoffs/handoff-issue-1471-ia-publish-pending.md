---
type: "Handoff"
id: "handoffs/handoff-issue-1471-ia-publish-pending"
title: "Finish issue #1471's TJRO 2026 pilot: publish candidate to Internet Archive, real candidate read-back proof, advance/revise/hold decision"
created_at: "2026-09-15T00:43:40.157340Z"
status: "active"
created_by_run: "runs/20260915T002743Z-do-the-best-useful-work-available-in-this-reposi"
state: "handoffs/handoff-issue-1471-archive-readback-v2's item 3 (real-browser CORS confirmation for issue #1482) is done -- PR #1489, docs/planning/evidence/archive-cors-probe-real-browser.json. Items 1/2/4 remain exactly as before: no IA_ACCESS_KEY/IA_SECRET_KEY in this environment (confirmed again this round), so the reordered comunicacoes.parquet candidate for djen-tjro-2026 still cannot be published, no apples-to-apples real read-back against it exists, and issue #1471's advance/revise/hold decision cannot yet be recorded (it is gated on that read-back per the issue's own acceptance criteria). This is the sixth consecutive round (since 2026-09-11) to reconfirm this exact same credential gap; a future round with IA write access should treat it as immediately actionable rather than re-diagnosing."
next_action: "Once IA write credentials are available: (1) publish the candidate (numero_processo-reordered, layout_revision=2) comunicacoes.parquet as a pilot to djen-tjro-2026, preserving rollback -- keep the currently published file recoverable, do not delete/overwrite without a documented way back; (2) run scripts/benchmarks/pilot_tjro_2026_real_archive_readback.py's technique (already proven this round's predecessor handoff, real metadata/head-range/tail-range probes + native DuckDB cold/warm timing) against the newly published candidate for a true apples-to-apples real-Archive comparison against docs/planning/evidence/pilot-tjro-2026-real-archive-readback.json's old-file baseline; (3) only after that read-back is validated, record issue #1471's advance/revise/hold decision with agreed regression limits, using PR #1480's local-simulation numbers and the old-file real numbers together as the baseline -- do not promote catalog/certification before that read-back is validated, per the issue's own text."
references: ["https://github.com/franklinbaldo/causaganha/issues/1471", "https://github.com/franklinbaldo/causaganha/issues/1472", "https://github.com/franklinbaldo/causaganha/pull/1480", "https://github.com/franklinbaldo/causaganha/pull/1483", "https://github.com/franklinbaldo/causaganha/pull/1489"]
goals: []
repository_head: "ca795fbcc08d89ff717139687705b5ee803c987c"
repository_branch: "claude/exciting-mccarthy-vdj7ti"
repository_dirty: true
repository_diff_digest: "sha256:030424b3e6409a188dcd23f6f9bfd389f4876ef8b455c27ad3ce2aae98f70a2f"
target_session_type: "session-types/standard-experience"
---

# Handoff
