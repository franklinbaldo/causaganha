---
type: AgentCheck
id: "2026-09-06-exciting-mccarthy-fpldz1-check-okf-parser-final"
run_id: "2026-09-06-exciting-mccarthy-fpldz1"
goal_id: "2026-09-06-exciting-mccarthy-fpldz1-goal-continue-with-agent"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "passed"
evidence_id: "2026-09-06-exciting-mccarthy-fpldz1-evidence-okf-generator-drift-caught"
summary: "Run repeatedly through the round (baseline 525 concepts before this round's own report existed; 539 concepts / 0 diagnostics / conformant=true with this round's full readings/goal/decision/evidence/check tree in place). Structural integrity (primary/foreign keys, enum values) holds throughout; the one real gap this round's own checks surfaced — a missing NOT NULL `reference` field on one AgentEvidence document, which silently widened the generated Zod contract — was caught by the separate completeness/generated-bindings pytest gates, not by this structural check alone, and is fixed (see evidence-okf-generator-drift-caught)."
---

# Check: okf-parser final

Bundle conformante ao final da rodada (539 conceitos, 0 diagnósticos), com a árvore completa desta rodada incluída.
