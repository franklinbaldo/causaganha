---
type: AgentEvidence
id: "2026-09-26-exciting-mccarthy-p08457-evidence-mechanical-verification"
run_id: "2026-09-26-exciting-mccarthy-p08457"
goal_id: "2026-09-26-exciting-mccarthy-p08457-goal-1051-test-split-adjudication"
kind: "other"
reference: "verificacao ao vivo via segmenter_dataset.store._text_element_to_labels e segmenter_dataset.mechanical.validate_record, antes de qualquer escrita no store"
summary: "Para cada uma das 2 segundas anotacoes independentes e das 2 resolucoes de adjudicacao, a reconstrucao verbatim (tags removidas == texto do documento armazenado) e a validacao mecanica (validate_record, sem overrides exceto o allowed_unmatched de 'ementa' ja documentado pela guideline para o formato capa+ementa-estruturada) foram confirmadas ANTES de qualquer escrita real. A segunda anotacao original do TRF6 (subagente haiku) tinha um bug estrutural real (ref_processual aninhado dentro do wrapper cabecalho_inicio, produzindo overlap) -- detectado por esta verificacao, corrigido estruturalmente (sem alterar conteudo/julgamento), e reverificado limpo antes da ingestao. A segunda anotacao do TRF2 passou limpa na primeira verificacao."
---

# Evidencia: verificacao mecanica pre-ingestao (2 anotacoes + 2 resolucoes)

`_text_element_to_labels` + `validate_record` rodados diretamente
(nao via autorrelato do subagente) para as 2 segundas anotacoes e as 2
resolucoes de adjudicacao, antes de qualquer escrita no store. TRF6
revelou um bug estrutural real (overlap por aninhamento incorreto),
corrigido e reverificado; TRF2 passou limpo de primeira.
