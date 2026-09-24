---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-e3tk18-check-governance-status"
run_id: "2026-09-24-exciting-mccarthy-e3tk18"
goal_id: "2026-09-24-exciting-mccarthy-e3tk18-goal-fix-dead-ref-normativa-overlap-detector"
command: "uv run python scripts/segmenter_governance_status.py"
result: "observed"
evidence_id: "2026-09-24-exciting-mccarthy-e3tk18-evidence-green-fix-and-real-corpus-clean"
summary: "0m56.5s, document_count=193, annotation_count=250, val_ceiling=test_ceiling=29 -- identico ao estado pre-rodada (fix de ferramenta de auditoria, nao lote de ingestao, nao deveria alterar esses numeros). Sem regressao de performance (continua rapido desde o fix de dedup.py de rodadas anteriores)."
---

# Check: governance status pos-fix

Reconfirma que o fix do detector `ref_normativa_overlap` nao alterou
`document_count`/`annotation_count`/ceilings de split, como esperado
para uma mudanca de ferramenta de auditoria (nao de dados).
