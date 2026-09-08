---
type: AgentCheck
id: "2026-09-08-exciting-mccarthy-izm703-check-okf-parser-baseline"
run_id: "2026-09-08-exciting-mccarthy-izm703"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "observed"
summary: "Run right after the scaffold + the three initial readings, before this round's own AgentRun frontmatter (id/started_at/etc.) was filled in. Result: conformant=false, 3 OKF022 diagnostics, all the same expected shape -- 'AgentReading_run_id_id_fkey has no matching AgentRun(id) for izm703' -- because run.md's own id field was still the scaffold's empty string at that point. concept_count=769 (up from obl3ux's close-time count, reflecting main's advance via #1319/#1323/#1325 since obl3ux). No other diagnostics. This is the same self-resolving gap every prior round in this family has hit at this exact stage; it clears once run.md's id field is filled in (see check-okf-parser-mid-round)."
---

# Check: okf-parser, linha de base

Rodado logo após o scaffold e as três leituras iniciais, antes do `run.md` ter seu próprio `id` preenchido. 3 diagnósticos OKF022 esperados (FK de `AgentReading.run_id` sem `AgentRun.id` correspondente) -- resolvem assim que o `run.md` desta rodada for preenchido.
