---
type: AgentEvidence
id: "2026-09-19-exciting-mccarthy-gbf44b-evidence-batch22-ingested"
run_id: "2026-09-19-exciting-mccarthy-gbf44b"
goal_id: "2026-09-19-exciting-mccarthy-gbf44b-goal-djen-sample-batch22"
kind: "diff"
reference: "docs/planning/evidence/segmenter-djen-sample-batch22-candidates.json, docs/planning/evidence/segmenter-djen-sample-batch22-overrides.json, data/segmenter/documents/*.xml, data/segmenter/annotations/*/"
summary: "6 documents ingested into data/segmenter via scripts/ingest_djen_sample_technique1_batch.py: TJGO/543564741, TJPB/578900185, TJPA/576803379, TJPA/576805366, TJRJ/327508788, TJTO/285747298. document_count 167->173, annotation_count 220->226, val_ceiling=test_ceiling=26 (was 25/25), confirmed live via scripts/segmenter_governance_status.py and git status --short data/segmenter (exactly 6 new documents/*.xml and 6 new annotations/<id>/, no silent no-op)."
---

# Evidencia: lote 22 ingerido

Seis subagentes independentes (um por documento) produziram a anotacao
Technique 1 canonica. Verificacao independente programatica (nao
apenas o autorrelato de cada subagente) via
`segmenter_dataset.store._text_element_to_labels` confirmou fidelidade
verbatim byte-a-byte contra o `texto_limpo` de cada candidato apos
correcao de dois defeitos reais encontrados nesta verificacao:

1. TJGO/543564741: substituicao NBSP->espaco/quebra-de-linha em 5
   posicoes -- corrigida pelo proprio subagente numa segunda passada
   (confirmado: a segunda notificacao de conclusao do agente relatou a
   correcao, e a reverificacao independente desta rodada confirmou
   match exato).
2. TJPA/576803379: 3 ocorrencias de `&` bruto (nome de parte "MORETTI &
   MACIEL LTDA") nao escapadas como entidade XML, causando erro de
   parsing (`not well-formed (invalid token)`) -- corrigido com
   substituicao regex `&` -> `&amp;` (preservando qualquer entidade ja
   existente), sem alterar o conteudo textual reconstruido (a funcao de
   parsing ja desescapa entidades XML de volta para `&`).

Apos as correcoes, `uv run python /tmp/.../verify_batch22.py` (script
que usa a mesma `_text_element_to_labels` de producao, nao uma
reimplementacao paralela) confirmou `verbatim_match=True` para os 6
documentos.

Tres overrides `--allowed-unmatched-overrides` foram declarados, cada
um verificado contra o texto-fonte bruto antes de declarar (nenhum
assumido por padrao):

- `capitulo_merito` em TJPA/576803379: o raciocinio de merito
  ("Decido. O feito comporta julgamento antecipado...") flui direto
  para o `dispositivo_abertura` ("Ante o exposto") sem frase de
  fechamento distinta -- confirmado lendo o texto entre a ultima frase
  de merito e a abertura do dispositivo.
- `custas`/`honorarios` em TJRJ/327508788: "Custas antecipadas.
  Honorários na forma da lei." -- dois enunciados curtos e distintos,
  mas nenhum com marcador de abertura/fechamento proprio.
- `custas`/`honorarios` em TJPB/578900185: "Sem custas e honorários
  advocatícios, nos termos do artigo 55 da Lei nº 9.099/95." -- clausula
  combinada unica cobrindo ambas as categorias, mesmo padrao ja
  sancionado em lotes anteriores (12/18/20).

`scripts/segmenter_semantic_audit.py` sinalizou 1 achado novo
(`fundamentacao_legal_collapsed` em TJTO/285747298,
`doc_12f989ac213c5eadf857aacc69b33ad2`) -- revisado manualmente contra o
texto-fonte: as ocorrencias adicionais de "art." estao (a) dentro de um
bloco de ementa de precedente do STJ (REsp 1.804.804/MS) citado
verbatim e ja coberto por uma unica tag `ref_normativa` para o proprio
precedente, e (b) dentro de uma transcricao literal do texto legal (Lei
11.101/2005 arts. 50/59, CPC art. 584) tambem ja coberta por
`fundamentacao_legal`+`ref_normativa` na frase introdutoria -- mesma
classe de falso positivo da heuristica (conta substring bruta de "art."
sem excluir blocos ja cobertos por uma tag mais ampla) ja documentada
para 5+ documentos pre-existentes do corpus nos lotes 12/20.

`scripts/segmenter_governance_status.py` confirma `document_count`
167->173, `annotation_count` 220->226, `val_ceiling`/`test_ceiling`
25/25->26/26 -- ainda abaixo do piso RFC 0012 Sec 5 item 4
(`corpus_scale_blocks_floor: true`). `git status --short data/segmenter`
confirmou exatamente 6 novos `documents/*.xml` e 6 novos
`annotations/<id>/`, sem write no-op silencioso.
