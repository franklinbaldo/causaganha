---
type: "RunReading"
id: "run-readings/20260907t214503z-do-the-best-useful-work-availab/reading-wiki"
run: "runs/20260907T214503Z-do-the-best-useful-work-available-in-this-reposi"
kind: "wiki"
subject: "Existing durable Wisk wiki state"
reference: ".wisk/knowledge/wiki/"
finding: "One WikiEntry exists: continuous-loop-operational-invariants.md. This round's finding extends it further: a third same-day bug in circuit_breaker.py (after c352943, b383135), all three found by treating the module's real callers (ia_s3.py's sync path vs. archive.py/engine.py/drain.py's async path) as the source of truth rather than the module in isolation -- the sync/async split in this shared class is a recurring source of latent defects, worth naming explicitly as its own pattern rather than three unrelated coincidental bugs."
---

# RunReading
