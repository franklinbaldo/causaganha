---
type: "RunEvidence"
id: "run-evidence/20260909t072455z-do-the-best-useful-work-availab/evidence-repair-run-observed"
run: "runs/20260909T072455Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "scripts/repair_segmenter_semantic_audit_2026_09.py"
summary: "Ran the repair script against data/segmenter: wrote 13 superseding AnnotationRecords (new annotator_id agent_repair:semantic_audit_2026_09, completed_at later than the flawed historical_migration ones) adding the missing distinct fundamentacao_legal/valor_condenacao anchors, validated per-record via mechanical.validate_record before writing. Re-ran scripts/segmenter_semantic_audit.py: findings dropped from 14 to 1 (doc_d61aecbf08b525a26f908f655285fe6c, reviewed and confirmed correct — its extra 'R$' mentions are the disputed arresto claim value, not a condemnation amount, so the >2 heuristic is a genuine false positive there, documented in the repair script and the new regression test)."
goal: "run-goals/20260909t072455z-do-the-best-useful-work-availab/goal-repair-segmenter-audit-1050"
---

# RunEvidence
