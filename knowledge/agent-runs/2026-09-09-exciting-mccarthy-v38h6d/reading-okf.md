---
type: AgentReading
id: "2026-09-09-exciting-mccarthy-v38h6d-reading-okf"
run_id: "2026-09-09-exciting-mccarthy-v38h6d"
subject: "OKF knowledge bundle continuity"
reference: "knowledge/agent-runs/2026-09-09-exciting-mccarthy-qvqmci/run.md, knowledge/agent-runs/2026-09-09-exciting-mccarthy-qhtc8c/run.md, knowledge/agent-runs/2026-09-09-exciting-mccarthy-ez5wkn/run.md, knowledge/backlog/*.md"
finding: "19+ AgentRun reports today, each fixing one verified bug via RED->GREEN->merge and closing its own PR in the next round. Two leads are explicitly declined across 5+ consecutive rounds (dead code in web/src/lib/coverageInsights.ts; download_zip()'s 403-vs-DJENRateLimitedError typing gap in src/djen_backup/djen.py) -- not worth re-raising without new evidence. Two concrete not-yet-picked-up leads surfaced by the two most recent rounds' own next_move notes: (1) qhtc8c flagged src/djen_backup/archive.py's token-bucket/circuit-breaker interaction under real concurrent load as unfuzzed, and 'remaining web/src/lib/*.ts modules' as an under-swept area; (2) ez5wkn flagged that processos_unificados/_UNIFICADOS_SQL's FULL OUTER JOIN only has one join-key test, not broader coverage of its n_fontes/fontes/tem_datajud aggregation logic across more than one CNJ. `uv run okf-parser check knowledge --relational-schema okf.schema.sql` on this round's own starting state (draft run.md, id 2026-09-09-exciting-mccarthy-v38h6d) returned conformant:true, concept_count:1113, 0 diagnostics -- the bundle is structurally sound at the start of this round."
---

# OKF knowledge reading

See `finding`. This round dispatched a background Explore-agent survey (in progress) that was pointed at the same declined/under-swept areas named here, to avoid re-deriving ground already covered and to weight the two concrete breadcrumbs from qhtc8c/ez5wkn.
