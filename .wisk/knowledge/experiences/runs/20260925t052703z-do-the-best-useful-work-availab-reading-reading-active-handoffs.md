---
type: "RunReading"
id: "run-readings/20260925t052703z-do-the-best-useful-work-availab/reading-active-handoffs"
run: "runs/20260925T052703Z-do-the-best-useful-work-available-in-this-reposi"
kind: "active-handoffs"
subject: "Active Handoffs"
reference: ".wisk/knowledge/experiences/handoffs/*.md (status field)"
finding: "Two active handoffs: handoff-issue-1471-ia-publish-pending (blocked on missing IA write credentials, reconfirmed absent again this round via evidence-credential-gap-still-absent -- 12th+ consecutive reconfirmation, disposed as reframed) and handoff-issue-1610-artifact-url-followup (created 2026-09-25T01:40, asks to (a) port artifact-URL validation to TypeScript and (b) audit other consumers of indice_processual.parquet's arquivo_ia_url outside service.py -- (a) is done, PR #1624 merged after this handoff was written. (b) is NOT done: grep found scripts/render_queries.py::_register_comunicacoes interpolating unvalidated arquivo_ia_url values directly into a read_parquet([...]) SQL string, the exact vulnerability class #1610 already fixed elsewhere -- undiscovered until this reading. This becomes this run's goal."
---

# RunReading
