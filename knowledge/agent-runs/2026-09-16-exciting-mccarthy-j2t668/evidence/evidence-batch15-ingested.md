---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-j2t668-evidence-batch15-ingested"
run_id: "2026-09-16-exciting-mccarthy-j2t668"
goal_id: "2026-09-16-exciting-mccarthy-j2t668-goal-djen-sample-batch15"
kind: "diff"
reference: "commit f622d4f (feat(segmenter): ingest fifteenth real multi-tribunal batch), commit 3746def (regression test), docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py (reused), /tmp scratch fix_nbsp.py (this round's own NBSP-restoration tool)"
summary: "6 real documents ingested into data/segmenter (TST/237077375, TJRJ/327515150, TJRJ/327497197, TJTO/285693071, TJTO/285710292, TRF2/301247724), confirmed by scripts/segmenter_governance_status.py: document_count 126->132, annotation_count 179->185, val_ceiling/test_ceiling 19/19->20/20. git status --short data/segmenter confirmed exactly 6 new documents/*.xml and 6 new annotations/<id>/ directories -- no silent duplicate/no-op writes (risk class 9/12 checked and ruled out)."
---

# Evidence: lote 15 ingerido no store do segmentador

`scripts/ingest_djen_sample_technique1_batch.py` rodado duas vezes: a
primeira tentativa (sem overrides) ingeriu 2/6 e sinalizou 2 pares
pendentes sem cue de fechamento (`capitulo_merito` em TST, `encerramento`
em TJTO/285710292) e 2 mismatches de fidelidade verbatim (TJTO/285693071,
TRF2/301247724).

Os 2 mismatches de fidelidade foram diagnosticados por diff programatico
(`difflib.SequenceMatcher`) como o defeito ja conhecido de NBSP (U+00A0)
normalizado para espaco comum durante a transcricao do subagente -- mas,
diferente de lotes anteriores (uma unica ocorrencia, corrigida com um
`str.replace` manual), aqui o defeito era pervasivo (12 e 33 ocorrencias
respectivamente). Corrigido com um script proprio desta rodada
(`fix_nbsp.py`, mantido apenas no scratchpad -- nao promovido a
`scripts/` por ser um caso de uso pontual) que mapeia cada posicao do
texto reconstruido (tags removidas) de volta para a posicao correspondente
no texto marcado, verifica que TODA diferenca e exclusivamente
NBSP-para-espaco (ou NBSP apagado em contexto so de whitespace) antes de
tocar em qualquer coisa, aplica a correcao, e reverifica byte-a-byte
antes de escrever -- sem retipar nada manualmente, sem pedir redo ao
subagente.

Apos a correcao de NBSP e a adicao de overrides revisados para 4 pares
pendentes (`capitulo_merito` x2, `custas` x2, `honorarios` x2,
`encerramento` x1, cada um verificado contra o texto-fonte bruto antes de
declarar -- ver `docs/planning/evidence/` do lote e a mensagem do commit
`f622d4f`), a segunda tentativa ingeriu os 6/6 documentos.
