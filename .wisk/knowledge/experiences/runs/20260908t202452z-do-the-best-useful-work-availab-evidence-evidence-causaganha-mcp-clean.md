---
type: "RunEvidence"
id: "run-evidence/20260908t202452z-do-the-best-useful-work-availab/evidence-causaganha-mcp-clean"
run: "runs/20260908T202452Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "Explore-agent audit: read all 18 .py files (~3,400 lines) under src/causaganha_mcp/, cross-referenced against djen_backup/djen.py, service.py, published.py, datajud client/service, and canary_heartbeat_check.py"
summary: "No confirmed bug matching any of the six known drift patterns (DJEN 200-vs-body classification, uncaught DJENNotFoundError/DJENRateLimitedError, blind except Exception, dead code, doc drift, sync/async dual-caller hazard). causaganha_mcp never calls djen.py's get_caderno_url transitively; all 28 except clauses are specifically typed; every locally-defined symbol has a real call site; spot-checked docstrings match actual control flow; all async DataJud clients are constructed fresh per call with no shared mutable state. Directory confirmed clean -- negative finding, per this goal's own success criteria, moves the sweep to the next unaudited area (src/datajud/, src/causaganha/decisoes, src/causaganha/processos, per the auditor's own suggestion)."
goal: "run-goals/20260908t202452z-do-the-best-useful-work-availab/goal-audit-causaganha-mcp"
---

# RunEvidence
