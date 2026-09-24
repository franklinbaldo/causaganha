---
type: AgentEvidence
id: "2026-09-20-exciting-mccarthy-x3954c-evidence-runtime-measurement"
run_id: "2026-09-20-exciting-mccarthy-x3954c"
goal_id: "2026-09-20-exciting-mccarthy-x3954c-goal-dedup-quadratic-fix"
kind: "runtime"
reference: "medicao ao vivo antes e depois da correcao, sobre o corpus real em data/segmenter (191 documentos, 1.38MB de texto normalizado)"
summary: "Antes: amostra de 200 pares aleatorios levou 5.437s (27.185 ms/par), projetando ~493s (>8min) para o scan completo de find_near_duplicates sobre os 18.145 pares do corpus real de 191 documentos -- confirmado empiricamente como hang real (processo morto apos >8min de CPU a 99.9% sem produzir saida, nao apenas uma projecao teorica). Depois: uv run python scripts/segmenter_governance_status.py completo (que inclui essa etapa mais list_documents/list_annotations/list_reviews/duas chamadas a assign_splits) rodou em 1m6.470s de tempo real, contra o hang anterior de >8min so na etapa de dedup -- reducao de pelo menos ~7-8x no gargalo isolado."
---

# Evidência: medição de runtime antes/depois

## Antes (implementação original, sem poda)

Amostra de 200 pares aleatórios do corpus real (`data/segmenter`,
191 documentos, textos normalizados de 1571 a 20905 caracteres, mediana
5483):

```
num documents 191 expected pairs 18145
text length stats: min 1571 max 20905 median 5483 sum 1258020
sampled 200 pairs in 5.437s -> 27.185 ms/pair
estimated total for all 18145 pairs: 493.3s
```

Confirmado como comportamento real (não só projeção): rodar
`uv run python scripts/segmenter_governance_status.py` diretamente
sobre o corpus real ficou preso a 99.9% de CPU por mais de 8 minutos
sem produzir a saída JSON esperada, tanto num ambiente com `.venv`
frio (primeira tentativa, que também baixou ~200MB de dependências
antes de começar a rodar o script) quanto num ambiente já aquecido
(segunda tentativa, processo morto manualmente após >100s de CPU só
para confirmar que não era custo de `uv sync`).

## Depois (poda por limite de comprimento + `quick_ratio`)

```
$ time uv run python scripts/segmenter_governance_status.py
{
  "document_count": 191,
  "annotation_count": 244,
  "review_count": 31,
  "train_eligible_count": 191,
  "evaluation_eligible_count": 31,
  "blocked_on_reviews": false,
  "val_count": 29,
  "test_count": 2,
  "val_ceiling_at_full_adjudication": 29,
  "test_ceiling_at_full_adjudication": 29,
  "meets_rfc_0012_split_floor": false,
  "corpus_scale_blocks_floor": true
}

real	1m6.470s
user	1m6.418s
sys	0m0.045s
```

66 segundos para o script inteiro (que inclui I/O de 191+244+31
arquivos e duas chamadas completas a `assign_splits`/`build_groups`),
contra um hang de mais de 8 minutos só na etapa de dedup antes da
correção. Os números reportados (`document_count=191`,
`annotation_count=244`, `val_ceiling=test_ceiling=29`) batem com o que
a PR #1597 já documentava para o estado pós-lote-25, confirmando que a
correção não alterou nenhum resultado substantivo — só o tempo.
