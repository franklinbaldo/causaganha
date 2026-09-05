---
type: AgentDecision
id: "2026-09-05-exciting-mccarthy-fnt3vx-decision-pr-1035-superseded"
run_id: "2026-09-05-exciting-mccarthy-fnt3vx"
goal_id: "2026-09-05-exciting-mccarthy-fnt3vx-goal-close-1048-pr-1035-superseded"
question: "#1048's last open checklist item asks to explicitly reassess PR #1035: should it be adapted to the now-canonical single-process opf train design, or superseded/closed as-is?"
choice: "Superseded, not adapted. Document the diff evidence on #1048 and close #1048 as completed; PR #1035 itself is already closed (unmerged) on GitHub and needs no further action beyond the explicit written reassessment #1048 asks for."
rationale: "Diffing PR #1035's branch (a50fadcc, based on a stale main commit 1f52358) against current main's scripts/run_segmenter_training.py shows #1035's core design change -- looping epoch-by-epoch with a subprocess hand-off between `opf train` calls to work around a claimed OPF RAM leak -- is precisely the design the module's current docstring names and rejects: 'Re-invoking opf train --epochs 1 per epoch (the pre-#1048 design) resets that optimizer/RNG state between epochs and diverges from the canonical semantics; it is not a co-equal alternative.' Adapting #1035 would mean re-deriving a design main has already deliberately moved past. Every piece of #1035 with standalone value -- exposing --learning-rate/--weight-decay/--grad-accum-steps/--max-grad-norm as overridable CLI flags -- is already present on main (scripts/run_segmenter_training.py argparse setup), and the defaults were already corrected from OPF's conservative built-in recipe (1e-5/0.01, what #1035 still hardcoded) to the upstream custom-label demo recipe #1048 calls for (2e-4/0.0). There is nothing left in #1035 to port."
---

# Decisão: PR #1035 é superada, não adaptada

O desenho central da #1035 (subprocessos por epoch) é exatamente o que o desenho canônico atual em `main` rejeita explicitamente. Todo conteúdo reaproveitável (as flags de otimização) já está incorporado sob o desenho correto. Não há nada a portar.
