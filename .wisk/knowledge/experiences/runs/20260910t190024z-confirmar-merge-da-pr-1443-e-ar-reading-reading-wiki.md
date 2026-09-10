---
type: "RunReading"
id: "run-readings/20260910t190024z-confirmar-merge-da-pr-1443-e-ar/reading-wiki"
run: "runs/20260910T190024Z-confirmar-merge-da-pr-1443-e-arquivar-o-handoff"
kind: "wiki"
subject: "wiki/continuous-loop-operational-invariants.md's scripts/*.py long-tail defect audit, remaining bootstrap_training_corpus.py and train_decision_segmenter.py leads"
reference: ".wisk/knowledge/wiki/continuous-loop-operational-invariants.md"
finding: "The third installment left bootstrap_training_corpus.py's nondeterministic hash()-based fallback id and train_decision_segmenter.py unread. This round's PR #1443 fixed the former (deterministic sha256 fallback id); this round also read the latter end-to-end and found it clean, closing the long-tail audit entirely."
---

# RunReading
