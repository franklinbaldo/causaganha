---
type: "RunReading"
id: "run-readings/20260910t175836z-confirmar-merge-da-pr-1434-e-ar/reading-wiki"
run: "runs/20260910T175836Z-confirmar-merge-da-pr-1434-e-arquivar-o-handoff"
kind: "wiki"
subject: "wiki/continuous-loop-operational-invariants.md's closing note on the except-Exception lineage and its pivot to the scripts/*.py long-tail defect audit"
reference: ".wisk/knowledge/wiki/continuous-loop-operational-invariants.md"
finding: "The prior entry closed the except-Exception lineage and pivoted to the long-tail defect audit named by PR #1408, listing 9 unread files. This round's PR #1434 read vendor_pje_swagger.py (clean) and evaluate_regex_segmenter.py (found and fixed a genuine dead-code bug: a skipped-segmentation counter was unreachable because pred_spans was coalesced from None to {} before the None-check). ia_practicality_probe.py was partially read and flagged (not fixed) for a dead 'warnings' field."
---

# RunReading
