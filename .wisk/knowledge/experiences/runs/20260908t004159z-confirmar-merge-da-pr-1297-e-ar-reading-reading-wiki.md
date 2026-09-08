---
type: "RunReading"
id: "run-readings/20260908t004159z-confirmar-merge-da-pr-1297-e-ar/reading-wiki"
run: "runs/20260908T004159Z-confirmar-merge-da-pr-1297-e-arquivar-o-handoff"
kind: "wiki"
subject: "Existing durable Wisk wiki state"
reference: ".wisk/knowledge/wiki/"
finding: "One WikiEntry exists: continuous-loop-operational-invariants.md. Two consecutive rounds (20260907T222723Z and 20260908T002654Z) independently hit and fixed the exact same fresh-checkout startup blocker -- 'wisk init .' had not been run, and the CLI's own no-eligible-session error gives no hint that the fix is 'run init', so a second round paid the same diagnosis cost. Separately, this round's reset_manifest fix is a fresh instance of a pattern CLAUDE.md already names for a different field (djen_raw as the sole canonical status signal, not any derived/mirrored field) -- worth recording so a future audit of any other function that mutates ia_status/djen_status remembers to check djen_raw too."
---

# RunReading
