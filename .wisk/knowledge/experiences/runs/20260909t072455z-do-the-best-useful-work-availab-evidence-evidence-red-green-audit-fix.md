---
type: "RunEvidence"
id: "run-evidence/20260909t072455z-do-the-best-useful-work-availab/evidence-red-green-audit-fix"
run: "runs/20260909T072455Z-do-the-best-useful-work-available-in-this-reposi"
kind: "diff"
reference: "scripts/segmenter_semantic_audit.py + tests/segmenter_dataset/test_segmenter_audit_scripts.py"
summary: "RED: added test_find_anti_patterns_ignores_superseded_annotation asserting a newer, corrected annotation clears a document's finding; failed against the old find_anti_patterns (it audited every historical annotation, including superseded ones). GREEN: added _latest_per_document() to find_anti_patterns, mirroring release.py's _latest_annotation train-split selection (RFC 0012 §10) — only the annotation a future release would actually use for training gets audited."
goal: "run-goals/20260909t072455z-do-the-best-useful-work-availab/goal-repair-segmenter-audit-1050"
---

# RunEvidence
