---
type: "Handoff"
id: "handoffs/handoff-issue-1471-pilot-validation"
title: "Start issue #1471's TJRO 2026 pilot validation, now unblocked by PR #1473"
created_at: "2026-09-14T14:33:06.402430Z"
status: "active"
created_by_run: "runs/20260914T142614Z-do-the-best-useful-work-available-in-this-reposi"
state: "PR #1473 (writer unification: unified Parquet writer, CNJ normalization, CNJ-first ordering, layout_revision bump to '2', footer KV_METADATA certification) merged to main as 4c13ef1. Issue #1470's audit baseline (11/09/2026) already identified djen-tjro-2026 (1,041,723 rows, 9 groups, 8 overlapping consecutive CNJ boundaries) as the concrete pilot candidate issue #1471 names. Nothing from #1471 has started yet: no PR references it (closed_by_pull_requests.total_count=0)."
next_action: "Follow issue #1471's acceptance criteria in order: preserve djen-tjro-2026's current comunicacoes.parquet with its identity/hash, run the now-merged writer (PR #1473, layout_revision=2) locally to produce a candidate version, then diff counts/identifiers/remaining fields between old and new (expecting only the documented CNJ normalization -- non-CNJ, NULL, mascara and leading zeros untouched, no silent loss/duplication). Then verify ordering/stats/schema/compression/footer contract, spot-check specific CNJs across group boundaries (including 7008332-16.2026.8.22.0007), measure date-only-query cost under the new ordering (DuckDB native + WASM, separating engine init / cold query / warm cache with bytes/requests/duration recorded), and only after a validated Archive read-back proof record the advance/revise/hold decision with regression limits. This is TDD-shaped: write the comparison/validation script and its assertions against the old vs. candidate parquet before deciding whether to expand the rollout -- do not promote catalog/certification before read-back is validated."
references: ["https://github.com/franklinbaldo/causaganha/issues/1471", "https://github.com/franklinbaldo/causaganha/issues/1470", "https://github.com/franklinbaldo/causaganha/pull/1473"]
goals: []
repository_head: "c59816fa9273fc0504013bfd0299d482d5c72689"
repository_branch: "claude/exciting-mccarthy-77cjzq"
repository_dirty: true
repository_diff_digest: "sha256:9f9163865e4bd1f25483ef78ff6c74878bf8c439c89207a74ffdf89231706957"
---

# Handoff
