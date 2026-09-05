---
type: AgentGoal
id: "2026-09-05-exciting-mccarthy-fnt3vx-goal-close-1048-pr-1035-superseded"
run_id: "2026-09-05-exciting-mccarthy-fnt3vx"
goal: "Close out issue #1048's last open checklist item ('reassess PR #1035 against this contract: simplify it to canonical single-process OPF training or supersede/close the noncanonical per-epoch machinery') with recorded diff evidence, and close #1048 itself since every other checklist item is already done on main."
rationale: "#1048's own comment thread (5551484815) already checks off 3 of 4 items (upstream OPF commit pinned #1101, macro-F1 zero-recall handling #1048/model_eval.py, best_epoch checkpoint selection #1126) and explicitly leaves PR #1035's reassessment as the only remaining, undecided item, calling it 'maior que este bugfix'. Diffing PR #1035 (closed, unmerged, mergeable_state=dirty, based on a stale main commit 1f52358) against current main's scripts/run_segmenter_training.py shows #1035 would reintroduce the exact per-epoch subprocess design the current module's own docstring says diverges from OPF's canonical single-continuous-invocation semantics -- while every CLI-flag addition #1035 proposed (--learning-rate/--weight-decay/--grad-accum-steps/--max-grad-norm) already exists on main under the canonical design, with defaults already corrected to the upstream custom-label recipe (2e-4/0.0) rather than #1035's conservative OPF built-in defaults (1e-5/0.01). This is a real, evidence-backed architectural decision (not busywork): it removes the segmenter roadmap's last blocker on treating #1048 as done, which #1047 lists as part of the critical path before #1053 (train a serious OPF baseline)."
success_signal: "A comment is posted on issue #1048 documenting the diff evidence and the explicit supersede decision, and the issue is closed as completed. No source code changes are required for this goal -- the canonical design is already on main; the gap was purely in issue bookkeeping."
status: "achieved"
---

# Goal: fechar o último item de checklist da issue #1048 (PR #1035 superada)

Decisão arquitetural registrada com evidência de diff: a #1035 não precisa de reavaliação de código porque seu desenho já foi descartado e todo conteúdo útil já foi incorporado pelo desenho canônico atual.
