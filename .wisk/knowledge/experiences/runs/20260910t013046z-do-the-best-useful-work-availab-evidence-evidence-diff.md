---
type: "RunEvidence"
id: "run-evidence/20260910t013046z-do-the-best-useful-work-availab/evidence-diff"
run: "runs/20260910T013046Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "git diff -- knowledge/okf.schema.sql tests/knowledge/test_backlog.py knowledge/backlog/"
summary: "Diff: okf.schema.sql drops last_verified_run_id's REFERENCES AgentRun(id) FK for a plain non-blank CHECK; tests/knowledge/test_backlog.py's FK-resolution test now accepts either a legacy knowledge/agent-runs/<id>/run.md path or a wisk:<run-id> reference resolved against .wisk/knowledge/experiences/runs/ by timestamp prefix; issue-1011.md/issue-1022.md/issue-985.md carry this round's live re-verification (still no IAS3 keys in env; TSE cdn.tse.jus.br still returns HTTP 403 Akamai Access Denied) with wisk: provenance and a real 2026-09-10T01:33:36Z timestamp; knowledge/backlog/index.md documents the new dual-format convention. Regenerated src/causaganha_mcp/_generated/domain_models.py and web/src/lib/processoConsultar.gen.ts (only the BacklogItem.last_verified_run_id field's x-okf-references/describe annotation dropped, per okf-parser's own generators)."
goal: "run-goals/20260910t013046z-do-the-best-useful-work-availab/goal-decouple-backlog-from-agentrun"
---

# RunEvidence
