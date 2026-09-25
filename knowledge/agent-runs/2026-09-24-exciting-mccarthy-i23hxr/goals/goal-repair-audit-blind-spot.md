---
type: AgentGoal
id: "2026-09-24-exciting-mccarthy-i23hxr-goal-repair-audit-blind-spot"
run_id: "2026-09-24-exciting-mccarthy-i23hxr"
goal: "Fechar um ponto cego real de teste em scripts/segmenter_semantic_audit.py (so 'collapsed' findings tinham regressao coberta), e usar essa cobertura ampliada para reparar, com evidencia mecanica (validate_record) e um teste RED->GREEN, os 4 defeitos semanticos reais que ela revela: 3 ancoras acordao_decisorio_inicio longas demais (viola Regra 1 do guideline) e 1 dispositivo_abertura marcado indevidamente dentro de um voto individual (viola a nota 'Acordao (second-instance)' do guideline)."
rationale: "Issue #1050 exige explicitamente 'corpus audit has no unresolved known semantic defects hidden as accepted gold'. As ~27 rodadas anteriores desta linhagem rodaram segmenter_semantic_audit.py repetidamente mas so validaram contra a allowlist dos 7 'collapsed' conhecidos -- os outros tipos de finding que o proprio script sabe detectar nunca tiveram nenhuma cobertura de teste, entao 4 defeitos reais presentes desde 2026-09-15 nunca foram notados nem corrigidos por nenhuma rodada. Corrigir isso e um avanco real e nao-duplicativo: nao colide com o batch27 em voo (PR #1605, de outra sessao), nao depende de credenciais externas, e reduz divida real de qualidade do corpus de treino que bloqueia a aceitacao final de #1050."
success_signal: "uv run python scripts/segmenter_semantic_audit.py contra data/segmenter nao reporta mais nenhum finding do tipo long_anchor ou dispositivo_inside_voto (so os 7 collapsed ja conhecidos permanecem); um novo teste de regressao (test_real_store_has_no_long_anchor_or_dispositivo_inside_voto_findings) fica GREEN tendo estado RED antes do reparo; uv run pytest -q tests/segmenter_dataset e a suite completa do repositorio permanecem verdes; document_count/annotation_count refletem as 4 novas AnnotationRecord supersedentes (246->250) sem alterar document_count nem os ceilings de split; ruff check/format --check e okf-parser check permanecem limpos."
status: "achieved"
---

# Objetivo: fechar o ponto cego de teste da auditoria semantica e reparar os 4 achados reais que ele escondia

O trabalho de dominio natural da linhagem `#1050` (mais um lote de
ingestao, batch28) foi deliberadamente adiado (ver `reading-prs`):
batch27 ja esta em PR aberta de outra sessao (`#1605`), e comecar um
lote concorrente antes dele mesclar repetiria o risco de colisao de
near-duplicate ja documentado (licao do batch14). Em vez disso, esta
rodada usa o tempo para reduzir uma divida de qualidade real e ate
agora invisivel: o unico teste de regressao sobre o corpus real de
`segmenter_semantic_audit.py` cobre apenas os findings `*_collapsed`
(ja triados exaustivamente como falsos positivos da heuristica em
`test_real_store_has_at_most_the_one_known_collapsed_false_positive`),
deixando os demais tipos de finding sem nenhuma rede de seguranca.
