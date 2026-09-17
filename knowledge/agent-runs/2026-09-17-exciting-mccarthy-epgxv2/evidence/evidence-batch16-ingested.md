---
type: AgentEvidence
id: "2026-09-17-exciting-mccarthy-epgxv2-evidence-batch16-ingested"
run_id: "2026-09-17-exciting-mccarthy-epgxv2"
goal_id: "2026-09-17-exciting-mccarthy-epgxv2-goal-djen-sample-batch16"
kind: "diff"
reference: "commit 99cc062 (feat(segmenter): ingest sixteenth real multi-tribunal batch), docs/planning/evidence/segmenter-djen-sample-batch16-2026-09-17.json, docs/planning/evidence/segmenter-djen-sample-batch16-fix-nbsp.py (reused batch15 technique)"
summary: "6 documents ingested into data/segmenter via scripts/ingest_djen_sample_technique1_batch.py: TST/237077398, TST/237077448, TJPI/22443818, TJPI/22443820, TJGO/543516662, TJPB/578832621. document_count 132->138, annotation_count 185->191, val_ceiling=test_ceiling=21 (was 20/20), confirmed live via scripts/segmenter_governance_status.py and git status --short data/segmenter (exactly 6 new documents/*.xml and 6 new annotations/<id>/, no silent no-op)."
---

# Evidencia: lote 16 ingerido

`git status --short data/segmenter` apos a ingestao final (com os 3
overrides declarados) mostrou exatamente 6 novos `documents/*.xml` e 6
novos `annotations/<id>/`, confirmando que nenhum dos 6 candidatos era
duplicata ja presente no store. `scripts/segmenter_governance_status.py`
confirma `document_count` 132->138, `annotation_count` 185->191,
`val_ceiling`/`test_ceiling` 20/20->21/21 -- ainda abaixo do piso RFC
0012 Sec 5 item 4 (`corpus_scale_blocks_floor: true`).

Dois defeitos reais encontrados e corrigidos durante a anotacao (nao no
codigo de producao):

1. TJGO/543516662 carregava entidades HTML brutas nao decodificadas no
   `texto_limpo` (411 ocorrencias de `&Aacute;` etc.) -- mesmo padrao
   recorrente do lote 12 para esse tribunal. Corrigido com
   `html.unescape()` antes de reanotar (a primeira tentativa de
   anotacao, sobre o texto com entidades, foi descartada e o candidato
   reanotado do zero sobre o texto corrigido).
2. TJPI/22443820 teve uma substituicao pervasiva de NBSP->espaco durante
   a transcricao do subagente (70 ocorrencias), corrigida com a mesma
   tecnica de diff-e-remapeamento programatico do lote 15
   (`docs/planning/evidence/segmenter-djen-sample-batch16-fix-nbsp.py`),
   E uma sub-anotacao genuina: o par `ementa` ficou sem `<fim>` apesar
   de uma cue de fechamento explicita existir na fonte ('5. Recurso
   conhecido e improvido.' logo antes do cabecalho ACORDAO) -- corrigido
   inserindo o `<fim>` ao redor do texto ja presente (nenhum conteudo
   retipado), com fidelidade verbatim reverificada byte-a-byte antes de
   declarar corrigido.
