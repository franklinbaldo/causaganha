---
type: AgentGoal
id: "2026-09-24-exciting-mccarthy-e3tk18-goal-fix-dead-ref-normativa-overlap-detector"
run_id: "2026-09-24-exciting-mccarthy-e3tk18"
goal: "Fechar os 4 tipos de finding de scripts/segmenter_semantic_audit.py que a rodada i23hxr deixou sem cobertura de teste (operative_on_reasoning_or_verb, capitulo_merito_on_prose, ref_processual_mismatch, ref_normativa_overlap), com fixtures sinteticas controladas por tipo (nao so contra o corpus real), e corrigir com TDD completo RED->GREEN o bug real que essa cobertura revelou: ref_normativa_overlap era codigo morto, pois comparava tags XML sem o atributo ord que o serializador da store sempre inclui, entao nunca disparava contra nenhum arquivo real."
rationale: "Issue #1050 exige explicitamente 'corpus audit has no unresolved known semantic defects hidden as accepted gold'. Uma heuristica de auditoria que nunca reportou um tipo de finding contra o corpus real ao longo de ~27+ rodadas nao e por si so evidencia de que o corpus esta limpo daquele defeito -- pode ser a propria heuristica que esta quebrada, como se confirmou aqui. #1605 (batch27, proximo passo de volume natural da linhagem) esta com mergeable_state=dirty numa branch de outra sessao que esta sessao nao pode editar sem permissao explicita (ver decision-defer-batch28-conflict-not-fixable-here), entao este e o avanco real, independente e imediatamente acionavel disponivel: fechar definitivamente a lacuna de teste que a propria rodada anterior identificou e nao pode ter ficado por resolver por mais uma rodada."
success_signal: "Um novo teste RED (test_find_anti_patterns_detects_ref_normativa_overlap) falha antes da correcao (fixture sintetica com fundamentacao_legal envolvendo um ref_normativa aninhado nao e detectada); apos trocar a checagem de substring/regex sem atributo por um regex que aceita atributos (<tag\\b[^>]*>), o mesmo teste fica GREEN. Mais 3 testes sinteticos novos (operative_on_reasoning_or_verb, capitulo_merito_on_prose, ref_processual_mismatch) e um novo teste de regressao contra o corpus real (test_real_store_has_no_operative_capitulo_processual_or_normativa_findings) tambem ficam GREEN. uv run python scripts/segmenter_semantic_audit.py contra data/segmenter continua reportando so os 7 achados collapsed ja conhecidos (nenhum achado novo revelado pelo fix -- corpus genuinamente limpo desses 4 tipos). document_count/annotation_count permanecem inalterados em 193/250 (fix de ferramenta, nao lote de ingestao). uv run ruff check/format --check, uv run pytest -q tests/segmenter_dataset e a suite completa do repositorio permanecem verdes. okf-parser check permanece conformant."
status: "achieved"
---

# Objetivo: fechar a ultima lacuna de teste da auditoria semantica e corrigir o detector morto que ela escondia

O trabalho de dominio natural da linhagem `#1050` (mais um lote de
ingestao, batch28) foi deliberadamente adiado (ver `reading-prs` e
`decision-defer-batch28-conflict-not-fixable-here`): `#1605` (batch27)
esta com conflito real de merge numa branch de outra sessao que esta
sessao nao pode resolver. Em vez disso, esta rodada terminou o
trabalho que `i23hxr` deixou explicitamente como proximo passo em seu
`next_move`: os 4 tipos de finding sem cobertura de teste que
sobraram apos aquela rodada fechar os outros dois.
