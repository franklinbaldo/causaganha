---
created_at: "2026-09-14T14:33:06.402430Z"
created_by_run: "runs/20260914T142614Z-do-the-best-useful-work-available-in-this-reposi"
goals: []
id: "handoffs/handoff-issue-1471-pilot-validation"
next_action: "Follow issue #1471's acceptance criteria in order: preserve djen-tjro-2026's current comunicacoes.parquet with its identity/hash, run the now-merged writer (PR #1473, layout_revision=2) locally to produce a candidate version, then diff counts/identifiers/remaining fields between old and new (expecting only the documented CNJ normalization -- non-CNJ, NULL, mascara and leading zeros untouched, no silent loss/duplication). Then verify ordering/stats/schema/compression/footer contract, spot-check specific CNJs across group boundaries (including 7008332-16.2026.8.22.0007), measure date-only-query cost under the new ordering (DuckDB native + WASM, separating engine init / cold query / warm cache with bytes/requests/duration recorded), and only after a validated Archive read-back proof record the advance/revise/hold decision with regression limits. This is TDD-shaped: write the comparison/validation script and its assertions against the old vs. candidate parquet before deciding whether to expand the rollout -- do not promote catalog/certification before read-back is validated."
references: ["https://github.com/franklinbaldo/causaganha/issues/1471", "https://github.com/franklinbaldo/causaganha/issues/1470", "https://github.com/franklinbaldo/causaganha/pull/1473"]
repository_branch: "claude/exciting-mccarthy-77cjzq"
repository_diff_digest: "sha256:9f9163865e4bd1f25483ef78ff6c74878bf8c439c89207a74ffdf89231706957"
repository_dirty: "true"
repository_head: "c59816fa9273fc0504013bfd0299d482d5c72689"
state: "PR #1473 (writer unification: unified Parquet writer, CNJ normalization, CNJ-first ordering, layout_revision bump to '2', footer KV_METADATA certification) merged to main as 4c13ef1. Issue #1470's audit baseline (11/09/2026) already identified djen-tjro-2026 (1,041,723 rows, 9 groups, 8 overlapping consecutive CNJ boundaries) as the concrete pilot candidate issue #1471 names. Nothing from #1471 has started yet: no PR references it (closed_by_pull_requests.total_count=0)."
status: "archived"
title: "Start issue #1471's TJRO 2026 pilot validation, now unblocked by PR #1473"
type: "Handoff"
continued_by_run: "runs/20260914T152436Z-do-the-best-useful-work-available-in-this-reposi"
archived_at: "2026-09-14T15:41:38.880940Z"
resolution: "reframed and superseded by handoffs/handoff-issue-1471-perf-and-readback: this round completed #1471's local diff/verification slice (PR #1478) but the remaining DuckDB perf measurement and Archive read-back proof need their own dedicated handoff with an Experience-typed target session, since they require a real IA publish rather than a knowledge-synthesis round."
---

# Handoff
