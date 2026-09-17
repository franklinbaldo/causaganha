---
type: AgentEvidence
id: "2026-09-17-exciting-mccarthy-726qh5-evidence-batch18-ingested"
run_id: "2026-09-17-exciting-mccarthy-726qh5"
goal_id: "2026-09-17-exciting-mccarthy-726qh5-goal-djen-sample-batch18"
kind: "diff"
reference: "commit b312222 (feat(segmenter): ingest eighteenth real multi-tribunal batch), docs/planning/evidence/segmenter-djen-sample-batch18-candidates.json, docs/planning/evidence/segmenter-djen-sample-batch18-overrides.json, docs/planning/evidence/segmenter-djen-sample-batch18-fix-missing-spaces.py"
summary: "6 real documents ingested into data/segmenter via scripts/ingest_djen_sample_technique1_batch.py (TJMT/74430633, TJRR/568209392, TJRR/568328945, TRF3/42490599, TRF5/349186353, TRF5/463264301). document_count 138->144, annotation_count 191->197, val_ceiling/test_ceiling 21/21->22/22, all confirmed live via scripts/segmenter_governance_status.py. Dry-run against a scratch copy of the store first (git-status-clean diff of exactly 6 new documents/*.xml, no unexpected duplicates) before the real ingest, which itself produced exactly 6 new documents/*.xml + 6 new annotations/<id>/ (git status --short data/segmenter)."
---

# Evidencia: lote 18 ingerido

Comando real executado (apos dry-run identico contra uma copia
descartavel do store em `/tmp/segmenter_dryrun`):

```
uv run python -m scripts.ingest_djen_sample_technique1_batch \
  --candidates docs/planning/evidence/segmenter-djen-sample-batch18-candidates.json \
  --tagged-dir /tmp/batch18_tagged \
  --output data/segmenter \
  --completed-at "2026-09-17T02:40:00Z" \
  --allowed-unmatched-overrides docs/planning/evidence/segmenter-djen-sample-batch18-overrides.json
```

Saida: `Ingested 6 document(s)` -- nenhum `Skipped`. `git status --short
data/segmenter` confirmou exatamente 6 `documents/*.xml` novos e 6
`annotations/<id>/` novos, sem no-op silencioso.

`scripts/segmenter_governance_status.py` ao vivo, antes e depois:

| Metrica | Antes (main, 706f92f) | Depois (branch, b312222) |
|---|---|---|
| document_count | 138 | 144 |
| annotation_count | 191 | 197 |
| val_ceiling | 21 | 22 |
| test_ceiling | 22 (era 21) | 22 |

Um defeito real de fidelidade verbatim foi encontrado e corrigido antes
da ingestao (TJRR/568328945: subagente omitiu 11 espacos ASCII isolados
ao redor de quebras de linha em branco, mismatch de 6368 vs 6385
caracteres) -- corrigido com uma tecnica nova de diff-and-remap
(`docs/planning/evidence/segmenter-djen-sample-batch18-fix-missing-spaces.py`),
generalizando a tecnica de remapeamento NBSP dos lotes 15/16 para
insercoes/substituicoes arbitrarias de whitespace, nao apenas
substituicoes de um unico caractere. Reverificado byte-a-byte apos a
correcao.

Nove overrides `--allowed-unmatched-overrides` foram declarados para
pares genuinamente sem cue de fechamento, cada um verificado contra o
texto-fonte bruto antes de declarar (ver
`docs/planning/evidence/segmenter-djen-sample-batch18-overrides.json`):
`custas` x4, `honorarios` x3, `relatorio` x3 (duas correspondencias
exatas ao padrao ja documentado no proprio guideline de anotacao --
"waiver clause is not a closing cue"), `capitulo_merito` x1 (fronteira
ambigua causada por um precedente citado verbatim embutido na
fundamentacao de TRF3/42490599).
