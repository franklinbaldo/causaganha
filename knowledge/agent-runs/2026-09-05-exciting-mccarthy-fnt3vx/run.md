---
type: AgentRun
id: "2026-09-05-exciting-mccarthy-fnt3vx"
started_at: "2026-09-05T21:28:00Z"
completed_at: "2026-09-05T22:05:00Z"
branch_at_start: "claude/exciting-mccarthy-fnt3vx"
commit_at_start: "c9d6eca45d800ba8cebbb1c5cd644a2c6f6a9cf2"
claude_md_reading_id: "2026-09-05-exciting-mccarthy-fnt3vx-reading-claude-md"
issues_reading_id: "2026-09-05-exciting-mccarthy-fnt3vx-reading-issues"
prs_reading_id: "2026-09-05-exciting-mccarthy-fnt3vx-reading-prs"
okf_reading_id: "2026-09-05-exciting-mccarthy-fnt3vx-reading-okf"
goal_ids:
  - "2026-09-05-exciting-mccarthy-fnt3vx-goal-purge-dead-experiment-imports"
  - "2026-09-05-exciting-mccarthy-fnt3vx-goal-close-1048-pr-1035-superseded"
primary_goal_id: "2026-09-05-exciting-mccarthy-fnt3vx-goal-purge-dead-experiment-imports"
considered_work:
  - "Pick up #1136 (standardize loading/empty/unavailable/error states) — its own newest comment explicitly gates it on PR #1160 (#1139's hierarchy fix) landing first, and #1160 is open-but-unmerged by a concurrent process; building on main now would be redone once #1160 reorders /publicacoes"
  - "Pick up #1131-1134 (other web/UX issues) — same concurrent-stack collision risk as #1136, since #1161 is actively consolidating /stats routes"
  - "#1093 (web(teor) busca direta de decisões) — explicitly marked 'NÃO é prioridade imediata' in its own body, gated on #950"
  - "#950 (MCP remote HTTP endpoint) — a live deploy/hosting decision, not autonomous-session-shaped without explicit sign-off"
  - "#1042 (prove update-catalog end-to-end) — requires observing a live GitHub Actions run with real IA-upload side effects, correctly deferred by every prior round"
  - "#1022 (publish TCU TEOR 2026 Parquet to Internet Archive) — READY, but the acceptance criteria are a live, hard-to-reverse public IA upload with real credentials; not something to do unattended without explicit sign-off"
  - "Redo exciting-mccarthy-ich5gz's lost #1107 availability-parity work — moot, a different concurrent process already closed #1107 via merged PR #1159 before this round started"
selected_work: "(1) Delete experiments/archive/test_all_improvements.py and experiments/archive/test_djen_api.py, both confirmed (live import check) to reference genuinely removed modules — the one #924 dead-code claim not already fixed by earlier rounds. (2) Close out issue #1048's last open checklist item by diffing PR #1035 against current main, confirming it is superseded by the canonical single-process opf train design already on main, and closing #1048 as completed."
expected_behavior: "experiments/archive/ no longer contains files that cannot execute due to removed imports, with the full Python gate (ruff check, ruff format --check, pytest -q) unaffected. Issue #1048 is closed with its full checklist checked off and a diff-backed record of why PR #1035 needed no further action."
entry_state: "new"
target_state: "merged"
decision_ids:
  - "2026-09-05-exciting-mccarthy-fnt3vx-decision-delete-not-exclude"
  - "2026-09-05-exciting-mccarthy-fnt3vx-decision-pr-1035-superseded"
evidence_ids:
  - "2026-09-05-exciting-mccarthy-fnt3vx-evidence-red-broken-imports"
  - "2026-09-05-exciting-mccarthy-fnt3vx-evidence-green-full-suite-post-delete"
  - "2026-09-05-exciting-mccarthy-fnt3vx-evidence-pr-1035-diff"
  - "2026-09-05-exciting-mccarthy-fnt3vx-evidence-issue-1048-closed"
check_ids:
  - "2026-09-05-exciting-mccarthy-fnt3vx-check-import-check-pre-delete"
  - "2026-09-05-exciting-mccarthy-fnt3vx-check-full-suite-post-delete"
  - "2026-09-05-exciting-mccarthy-fnt3vx-check-no-references-grep"
  - "2026-09-05-exciting-mccarthy-fnt3vx-check-pr-1035-diff-review"
  - "2026-09-05-exciting-mccarthy-fnt3vx-check-issue-1048-closed-check"
result_state: "review"
result_summary: "Two independent, non-web, non-colliding advances this round, both chosen after finding that most of the 'obvious' candidates (issue #1107, three of #924's five dead-code claims, both PENDING_REAL canary alarms) were already resolved by earlier rounds on live verification, and the remaining ready web/UX issues (#1136, #1131-1134) are gated on a concurrent process's in-flight, unmerged PR stack (#1160/#1161) that this round deliberately left untouched. (1) Deleted experiments/archive/test_all_improvements.py and experiments/archive/test_djen_api.py: live import checks confirmed 5/6 of their non-stdlib imports raise ModuleNotFoundError against genuinely-removed modules (causaganha.analysis.embedding_service_v2/embedding_models, causaganha.pipeline.embedding_pipeline, causaganha.storage.embedding_storage, causaganha.api.client). Chose outright deletion over ruff.toml's existing 'frozen documentation' carve-out (used for the legacy taxonomy notebooks) because neither file has any RFC/doc/test role, unlike those notebooks. ruff check, ruff format --check, and the full pytest -q suite (1463 passed, 1 skipped, exit 0) are identical before/after, confirming the deletion is a true no-op for every gate rather than a hidden regression (both files were already outside pytest's testpaths=[\"tests\"]). (2) Closed issue #1048 (segmenter: make OPF training semantics and checkpoint selection correct): its own comment thread had already checked off 3 of 4 checklist items via merged PRs #1101/#1104/#1126, leaving only 'reassess PR #1035' open. Fetched PR #1035's head (a50fadcc, closed unmerged, based on a stale main commit 1f52358) and diffed it against current main's scripts/run_segmenter_training.py: #1035 would reintroduce the exact per-epoch opf-train-subprocess design the current module's own docstring names and rejects as diverging from OPF's canonical semantics, and its DEFAULT_LEARNING_RATE/DEFAULT_WEIGHT_DECAY (1e-5/0.01, OPF's conservative built-in defaults) predate main's correction to the upstream custom-label recipe (2e-4/0.0) that #1048 calls for. Every CLI flag #1035 proposed already exists on main under the correct design and defaults, so nothing needed porting. Posted the diff evidence as a comment on #1048 and closed it as completed. Both changes committed to this branch; PR not yet opened as of this write (opened immediately after this report's first push, per the scaffold's completed_at-before-push rule)."
next_move: "No web/UX work should start until the concurrent #1160/#1161 stack merges (or is confirmed abandoned) — #1136 and #1131-1134 are the natural next web slice once that stack lands, per #1136's own readiness comment. Non-web candidates for a future round, in priority order: (1) #1053 (train a serious canonical OPF baseline) is now unblocked at the issue-tracker level since #1048 is closed, but it needs a real GPU run (Kaggle/Colab bridge) and is not a quick autonomous-session slice; (2) #1050/#1051 (repair/scale real training corpus, build independent adjudicated validation) are the actual critical-path blockers #1047 names before #1053 can produce a meaningful baseline, and are annotation-heavy, not code-only; (3) #1022 (publish TCU TEOR 2026 Parquet to Internet Archive) is READY at the issue level but is a live, hard-to-reverse public IA upload with real credentials — a future round should either get explicit sign-off first or treat it as an operational slice like #1042; (4) #1042 (prove update-catalog end-to-end) remains the standing operational slice requiring a live GitHub Actions run with real IA-upload side effects. A process note for the loop itself: exciting-mccarthy-ich5gz (the round immediately before this one) reached result_state='green' but never pushed its branch, and its work was lost when the container was reclaimed — this round's okf reading names it explicitly; future rounds should treat 'push the branch' as part of reaching 'done', not a follow-up step that can be silently skipped."
---

# Agent run — 2026-09-05-exciting-mccarthy-fnt3vx

Oitava rodada do loop horário do CausaGanha, orientada pelo scaffold `.claude/agent-run-scaffold.md`.

## O que aconteceu

1. **Leituras** (`readings/`): `CLAUDE.md`, issues abertas (28), PRs abertos (2, ambos de uma pilha concorrente em progresso para #1138/#1139, verdes e não precisando de ajuda) e conhecimento OKF (bundle conformante, todas as 7 rodadas anteriores do dia completas).
2. **Achado central da leitura de issues**: várias lacunas nomeadas por rodadas/issues anteriores já estavam de fato resolvidas quando verificadas ao vivo — #1107 fechada por PR concorrente, e três das cinco alegações de código morto da #924 já corrigidas. Isso redirecionou a rodada para as duas lacunas reais e não reivindicadas encontradas: arquivos órfãos em `experiments/archive/` e o último item de checklist da #1048.
3. Evitou deliberadamente `web/` inteiro nesta rodada, para não colidir com a pilha ativa de PRs #1160/#1161.
4. Ver `goals/`, `decisions/`, `evidence/` e `checks/` para o detalhe tipado de cada etapa.
