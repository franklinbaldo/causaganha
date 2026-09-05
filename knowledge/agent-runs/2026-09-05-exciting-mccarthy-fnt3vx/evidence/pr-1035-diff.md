---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-fnt3vx-evidence-pr-1035-diff"
run_id: "2026-09-05-exciting-mccarthy-fnt3vx"
goal_id: "2026-09-05-exciting-mccarthy-fnt3vx-goal-close-1048-pr-1035-superseded"
kind: "diff"
reference: "git diff origin/main pr-1035-check -- scripts/run_segmenter_training.py (pr-1035-check = PR #1035's head commit a50fadcc, fetched via refs/pull/1035/head)"
summary: "535-line diff. Two decisive findings: (1) PR #1035 replaces the module's canonical-single-invocation docstring/design with an epoch-by-epoch `opf train` subprocess loop ('Loops epoch-by-epoch with an explicit checkpoint hand-off between opf train subprocess calls ... a mechanical lesson RFC 0012 section 13.2 carries over from PR #832: the opf trainer leaks RAM in a long-lived process') -- exactly the pre-#1048 design the current main docstring explicitly names and rejects ('Re-invoking opf train --epochs 1 per epoch ... diverges from the canonical semantics; it is not a co-equal alternative'). (2) PR #1035's DEFAULT_LEARNING_RATE/DEFAULT_WEIGHT_DECAY are 1e-5/0.01 (OPF's conservative built-in defaults) where current main already has 2e-4/0.0 (the upstream custom-label demo recipe #1048 calls for) -- PR #1035 is based on a main commit (1f52358) that predates that correction, so its diff would regress the defaults if merged as-is. Every one of #1035's standalone-valuable CLI flags (--learning-rate/--weight-decay/--grad-accum-steps/--max-grad-norm) is already present on current main under the correct design and correct defaults."
---

# Evidência — diff da PR #1035 contra main atual

O diff mostra que a #1035 reintroduziria exatamente o desenho de subprocesso por epoch que o `main` atual rejeita explicitamente, e usaria defaults de otimização mais fracos (já corrigidos no `main`). Não há conteúdo aproveitável a portar.
