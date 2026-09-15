---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-2hb3sq-evidence-adjudication-decisions"
run_id: "2026-09-15-exciting-mccarthy-2hb3sq"
goal_id: "2026-09-15-exciting-mccarthy-2hb3sq-goal-scale-segmenter-reviews"
kind: "review"
reference: "data/segmenter/reviews/doc_b8a4a405e45ffe9a1ab11cf902f849e2/rev_b36dc072ea62772c5a50d6a42e9175e4.xml ; data/segmenter/reviews/doc_ec1f5133660dc174fe80e615f3f46dd2/rev_b0c50f8be7eddb9f7266345b007f1317.xml"
summary: "Em ambos os documentos, a resolucao final adotou a anotacao 'A' (llm_technique1:second_independent_f0q3d4, familia general-purpose) 100% das vezes sobre a nova anotacao 'B' desta rodada (llm_technique1:second_independent_2hb3sq, familia haiku) em todo disagreement: cabecalho_inicio, voto_inicio, acordao_decisorio_inicio/fim e resultado de B foram sistematicamente mais longos que o exemplo literal do guideline: e ementa_fim de B, no segundo documento, ancorou em texto de metadado Word/HTML espurio ('Normal 0 21 false false false PT-BR X-NONE X-NONE') em vez do ultimo enunciado real da ementa."
---

# Evidencia: decisoes de adjudicacao registradas em cada ReviewRecord

## doc_b8a4a405e45ffe9a1ab11cf902f849e2 (8 matched, 4 only_a, 4 only_b)

Todos os 4 disagreements sao a mesma categoria em A e B, so que com spans
diferentes -- adotado A em todos, por ser mais curto e bater com o exemplo
literal do guideline:

- `cabecalho_inicio`: A="PODER JUDICIARIO" (16 char) vs B="PODER JUDICIARIO
  DO ESTADO DE RONDONIA" (38 char) -- guideline cita literalmente "PODER
  JUDICIARIO" como exemplo; adotado A.
- `acordao_decisorio_inicio`: A="Vistos, relatados e discutidos" (31 char,
  identico ao exemplo do guideline) vs B a mesma frase estendida ate "...em
  que sao partes as acima indicadas" (127 char). Adotado A.
- `resultado`: A="CONHECIDOS E REJEITADOS" (verbo operativo puro, Regra 3)
  vs B incluindo o sujeito completo ("EMBARGOS DE DECLARACAO DO REQUERENTE
  E DO REQUERIDO CONHECIDOS E REJEITADOS A UN..."). Adotado A.
- `acordao_decisorio_fim`: A="A UNANIMIDADE, NOS TERMOS DO VOTO DO
  RELATOR." (fecha o resultado colegiado, exatamente a definicao da tabela
  do guideline: "'a unanimidade'/'por maioria' + close of the collegiate
  result") vs B estendendo ate a assinatura final do documento ("JUIZ(A)
  Enio Salvador Vaz RELATOR(A)"), que e bloco administrativo, nao o
  fechamento do resultado colegiado. Adotado A.

## doc_ec1f5133660dc174fe80e615f3f46dd2 (10 matched, 4 only_a, 5 only_b)

- `cabecalho_inicio`, `voto_inicio`, `acordao_decisorio_inicio`: mesmo
  padrao -- A mais curto e literal ("PODER JUDICIARIO", "VOTO", "Vistos,
  relatados e discutidos"), B sistematicamente mais longo (inclui nome do
  relator substituto, titulo da secao "ACORDAO" em vez da frase operativa).
  Adotado A nos 3.
- `ementa_fim`: A="o conceito social das partes." (ultima frase real do
  paragrafo da ementa) vs B="Normal 0 21 false false false PT-BR X-NONE
  X-NONE" -- literalmente metadado de exportacao Word/HTML que sobra no
  texto apos a ementa, nao conteudo da decisao. Erro real e inequivoco do
  subagente B; adotado A.
- `fundamentacao_legal` (so em B, sem par em A): B tageou "consoante se
  observa dos seguintes julgados:" como fundamentacao_legal -- essa frase
  e um conector que introduz uma lista de precedentes, nao cita ela mesma
  nenhuma norma (Regra do guideline distingue citacao de norma de mera
  frase de transicao). Rejeitado; A nao tem correspondente.

## Padrao consolidado (2/2 documentos, reforcando f0q3d4)

O subagente Tecnica 1 desta rodada (haiku) perdeu 100% dos disagreements
de fronteira para a anotacao mais antiga (general-purpose) por ancorar
sistematicamente mais longo que a Regra 1 do guideline pede, e uma vez
ancorou em metadado de exportacao espurio em vez de conteudo real. Isso
e o MESMO padrao de erro que f0q3d4 ja tinha registrado (2/2 documentos
daquela rodada) -- agora confirmado numa terceira e quarta observacao
independente (4/4 no total, entre as duas rodadas). Justifica reforcar o
prompt canonico de Tecnica 1
(`data/segmenter_splits/technique1_annotation_prompt.md`) com um exemplo
explicito de span CORRETO vs INCORRETO para `acordao_decisorio_fim`/
`resultado`, e um aviso especifico contra ancorar em metadado de
exportacao de documento (headers "Normal 0 21 false false false...").
Nao fiz essa mudanca de prompt nesta rodada para nao misturar uma mudanca
de metodologia com o incremento de dados desta rodada; registrado como
proximo avanco natural.
