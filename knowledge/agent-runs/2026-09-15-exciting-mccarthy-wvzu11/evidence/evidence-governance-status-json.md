---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-wvzu11-evidence-governance-status-json"
run_id: "2026-09-15-exciting-mccarthy-wvzu11"
kind: "runtime"
reference: "docs/planning/evidence/segmenter-governance-status-2026-09-15.json (gerado por scripts/segmenter_governance_status.py --store data/segmenter)"
summary: "Rodando a ferramenta contra a store real: document_count=61, annotation_count=74, review_count=0, train_eligible_count=61, evaluation_eligible_count=0, blocked_on_reviews=true. Confirma ao vivo, não por suposição, que a causa raiz de #1051 não avançar é a ausência total de ReviewRecords na store -- não um bug em assign_splits/EmptyEvalSplitError (que só protege contra grupos elegíveis famintos, não contra um conjunto elegível genuinamente vazio)."
---

# Evidência: comportamento real observado

```json
{
  "document_count": 61,
  "annotation_count": 74,
  "review_count": 0,
  "train_eligible_count": 61,
  "evaluation_eligible_count": 0,
  "blocked_on_reviews": true
}
```

Também confirmado manualmente antes da ferramenta existir: `uv run python -m segmenter_dataset assign-splits --data-root data/segmenter/ --output <tmp>/split_manifest.json --seed 771` produz `train=61 val=0 test=0`, divergindo do `data/segmenter_splits/manifest.json` commitado (train=14/val=3/test=3) que `.github/workflows/train-segmenter.yml` consome para treino real -- os `doc_id`s desse manifest commitado (ex.: `tjro_acordao_03`) nem sequer usam o esquema de ID da store nova (`doc_<hash32>`), confirmando que são linhagens de dados desconectadas.
