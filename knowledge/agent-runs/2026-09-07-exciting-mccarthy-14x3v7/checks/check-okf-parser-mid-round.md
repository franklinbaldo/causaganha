---
type: AgentCheck
id: "2026-09-07-exciting-mccarthy-14x3v7-check-okf-parser-mid-round"
run_id: "2026-09-07-exciting-mccarthy-14x3v7"
goal_id: "2026-09-07-exciting-mccarthy-14x3v7-goal-djen-retry-after-floor"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
summary: "conformant=true, 0 diagnostics, concept_count=706, markdown_count=709, reserved_count=3 — run after linking goal, evidence (RED+GREEN), one AgentCheck (web suite), and one AgentDecision (discard orval drift) into the bundle. Caught and fixed one real FK error along the way: check-okf-parser-baseline.md's evidence_id was an empty string, which okf-parser flagged as OKF022 (a foreign key referencing a non-existent '' AgentEvidence) rather than treating it as absent — fixed by matching the project's established AgentCheck shape (result: passed/failed/observed enum + separate free-text summary field, evidence_id omitted rather than empty) seen in prior rounds' check files, not just this round's own first draft."
evidence_id: "2026-09-07-exciting-mccarthy-14x3v7-evidence-green-retry-after"
---

# Check: okf-parser (meio da rodada)

Rodado após vincular goal, evidências (RED+GREEN), o check da suíte web e a decisão sobre o drift do orval. Conformante — 0 diagnósticos. Corrigiu-se no caminho um erro real de FK: `evidence_id: ""` no check baseline (string vazia não é tratada como ausente pelo schema) e o campo `result` livre em vez do enum `passed/failed/observed` esperado por `AgentCheck`.
