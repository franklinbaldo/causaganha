---
type: AgentEvidence
id: "2026-09-15-exciting-mccarthy-6kxfkh-evidence-review-doc-3cffd"
run_id: "2026-09-15-exciting-mccarthy-6kxfkh"
goal_id: "2026-09-15-exciting-mccarthy-6kxfkh-goal-scale-segmenter-reviews"
kind: "diff"
reference: "data/segmenter/reviews/doc_3cffd7961e9fc910f6ae628f5aaa6c40/rev_9d550aa9b704daa63cd5405c8ebbcbe7.xml"
summary: "ReviewRecord real adjudicando 3 categorias em disagreement entre a anotacao historica (ann_4a186cf9..., family prompt_subagents:haiku, seeded_with=none) e a nova segunda anotacao independente (ann_e741de94..., family prompt_subagents:general-purpose, seeded_with=none) de doc_3cffd7961e9fc910f6ae628f5aaa6c40 (acordao TJRO, formato capa+ementa-estruturada)."
---

# Evidencia: adjudicacao de doc_3cffd7961e9fc910f6ae628f5aaa6c40

Disagreements resolvidos:

- `cabecalho_fim`: adotado o limite da nova anotacao ("À UNANIMIDADE.")
  -- a historica parava em "DATA DA DISTRIBUIÇÃO: 28/03/2025", deixando
  "DECISÃO: RECURSO PARCIALMENTE PROVIDO NOS TERMOS DO VOTO DO RELATOR, À
  UNANIMIDADE." fora do cabecalho sem necessidade; o texto imediatamente
  seguinte e "Ementa:", entao o fim correto do bloco de capa e o ultimo
  texto antes dela.
- `resultado` (categoria de no maximo uma tag por documento, guideline
  linhas 21-22 e regra 3): adotado o limite da nova anotacao, na secao
  "IV. DISPOSITIVO E TESE" ("Recurso parcialmente provido para excluir a
  condenacao..."), o holding operativo de fato -- nao a linha de metadado
  "DECISÃO:" da capa que a historica tagueava. Regra 3 do guideline
  ("resultado only on the operative verb, not on ... quoted precedent
  outcomes") favorece o holding substantivo sobre o rotulo indexador da
  capa.
- `ementa_fim`: descartado por completo -- a historica tagueava
  "RECURSO PARCIALMENTE PROVIDO." no meio do primeiro paragrafo da ementa,
  mas o guideline v7 linha 46 e explicito: para este formato TJRO exato
  ("Ementa:" seguido diretamente por I/II/III/IV sem RELATÓRIO/VOTO
  separado), `ementa_fim` deve ficar sem par (`allowed_unmatched`),
  estendendo ate o fim do documento -- os quatro incisos numerados SÃO o
  conteudo publicado da ementa, nao uma secao depois dela. A nova
  anotacao seguiu essa regra corretamente desde a primeira tentativa.

Independencia verificada: `store.write_review` aceitou sem
`NonIndependentReviewError` (familias `prompt_subagents:haiku` vs
`prompt_subagents:general-purpose`, ambas `seeded_with="none"`).
