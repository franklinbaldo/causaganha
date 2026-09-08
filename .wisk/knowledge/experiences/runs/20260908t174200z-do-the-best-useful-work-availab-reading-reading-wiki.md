---
type: "RunReading"
id: "run-readings/20260908t174200z-do-the-best-useful-work-availab/reading-wiki"
run: "runs/20260908T174200Z-do-the-best-useful-work-available-in-this-reposi"
kind: "wiki"
subject: ".wisk/knowledge/wiki/continuous-loop-operational-invariants.md"
reference: ".wisk/knowledge/wiki/continuous-loop-operational-invariants.md (full read earlier this session, before goal selection)"
finding: "The 'shared classification/normalization function must be audited against every call site' pattern (already responsible for 5+ confirmed bugs: circuit_breaker.py x3, drain_unknowns.py, manifest.py/render_manifest_parquet.py) generalizes cleanly to this round's fix: backfill_probe.py's _probe_one was a sixth instance of the same root cause -- a DJEN-classification duplicate that drifted from the canonical get_caderno_url-based logic used by engine.py, djen_backup/probe.py, and drain_unknowns.py."
---

# RunReading
