---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-5lvbii-evidence-batch12-ingested"
run_id: "2026-09-16-exciting-mccarthy-5lvbii"
goal_id: "2026-09-16-exciting-mccarthy-5lvbii-goal-djen-sample-batch12"
kind: "runtime"
reference: "docs/planning/evidence/segmenter-djen-sample-batch12-candidates.json, docs/planning/evidence/segmenter-djen-sample-batch12-overrides.json"
summary: "Two independent subagents (Technique 1 canonical prompt) annotated TJES/577054686 (19 anchor tags, self-verified verbatim match) and TJGO/543562390 (27 anchors, self-verified verbatim match) as separate background agents writing to separate raw/tagged directories (per risk class 10 from knowledge/backlog/issue-1050.md: never share one directory between raw source and tagged output). First ingest attempt: TJES ingested clean (doc_f3b730a0...); TJGO failed mechanical validation with unmatched pairs ['capitulo_merito', 'custas'] -- verified against the raw source text (batch12_raw/543562390.txt) that neither pair has a real closing cue ('Decido.' opens capitulo_merito with no transition phrase before the next section; custas and honorarios share one sentence with only honorarios getting a distinct closing clause), matching the same risk-class-4-style pattern documented since batch4. Declared a reviewed override (segmenter-djen-sample-batch12-overrides.json) with the specific textual reasoning, re-ran ingestion: both documents ingested (doc_f3b730a0..., doc_d9de18ae...). git status --short data/segmenter confirmed 2 new document/annotation file pairs (not a concurrency collision -- both are genuinely new). grep -o 'ord=\"[0-9]*\"' ... | wc -l confirmed 14 and 20 real anchor positions respectively in the written XML (not the risk-class-10 zero-label defect). scripts/segmenter_governance_status.py live: document_count 119->121, matching goal-djen-sample-batch12's success_signal exactly (val/test ceiling unchanged at 18/18, 2 documents didn't cross the next ceiling step)."
---

# Evidência: lote 12 ingerido

TJES/577054686 e TJGO/543562390 ingeridos com sucesso após um override
revisado para dois pares pendentes sem cue de fechamento em TJGO
(verificado contra o texto-fonte antes de declarar). `document_count`
119->121 ao vivo, confirmado por `scripts/segmenter_governance_status.py`.
