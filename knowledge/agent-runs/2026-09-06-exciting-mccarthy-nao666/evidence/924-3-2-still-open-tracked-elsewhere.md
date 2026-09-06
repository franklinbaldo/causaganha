---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-nao666-evidence-924-3-2-still-open-tracked-elsewhere"
run_id: "2026-09-06-exciting-mccarthy-nao666"
goal_id: "2026-09-06-exciting-mccarthy-nao666-goal-close-924-live-verification"
kind: "other"
reference: "data/segmenter_splits/{val,test,train}.jsonl, data/segmenter_splits/manifest.json; issue #1047"
summary: "#924 §3.2 asked for a double-independent-annotation round to unblock RFC 0012's val/test gates. Live check: data/segmenter_splits/val.jsonl and test.jsonl exist (3 docs each, 14 in train) with manifest.json recording ensemble adjudication ('test_verified_by: prompt_ensemble:strict+disambig+blind+adversarial'), but the manifest's own notes call this a 'Single-tribunal (TJRO) seed of 20 docs; scale to more tribunals/volume next' — not the scaled, RFC-0012-§9.1-compliant independent double annotation the sub-item asks for. This item is genuinely still open, and is already tracked by issue #1047 (segmenter: evidence-first roadmap for the next training cycle) and its children #1050/#1051, so #924 does not need to stay open to track it."
---

# Evidência — #924 §3.2 permanece aberto, já rastreado em #1047

Existe uma seed minúscula (3+3 docs) adjudicada por ensemble, mas explicitamente marcada como não-escalada. O item real segue em #1047/#1050/#1051.
