---
type: AgentEvidence
id: "2026-09-05-exciting-mccarthy-9xpeua-evidence-red"
run_id: "2026-09-05-exciting-mccarthy-9xpeua"
goal_id: "2026-09-05-exciting-mccarthy-9xpeua-goal-copy-reference-action"
kind: "test_red"
reference: "web/src/lib/processoReference.test.ts, run before web/src/lib/processoReference.ts existed"
summary: "`npx vitest run src/lib/processoReference.test.ts` failed with a Vite import-resolution error ('Failed to resolve import \"./processoReference\"') before the module was created — the intended contract (no fabricated freshness/date placeholder, origin URL always ordered before the CausaGanha URL, plain text with no markdown/HTML) was written as a failing test first."
---

# Evidência RED

Suite de `processoReference.test.ts` escrita e executada contra um módulo inexistente, confirmando falha antes da implementação.
