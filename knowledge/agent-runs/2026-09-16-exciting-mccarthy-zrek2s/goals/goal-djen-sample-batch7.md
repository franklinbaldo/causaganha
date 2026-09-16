---
type: AgentGoal
id: "2026-09-16-exciting-mccarthy-zrek2s-goal-djen-sample-batch7"
run_id: "2026-09-16-exciting-mccarthy-zrek2s"
title: "Ingerir setimo lote real multi-tribunal para o corpus de treino do segmentador (#1050)"
motivation: "RFC 0012 Sec 5 item 4 exige piso >=30 documentos adjudicados em val e >=30 em test; o corpus real (nao-sintetico, multi-tribunal) ainda esta muito abaixo disso (document_count=96, val_ceiling=test_ceiling=14 verificado ao vivo nesta rodada). Seis lotes anteriores ja provaram que scripts/ingest_djen_sample_technique1_batch.py escala sem mudanca de codigo de producao; continuar essa cadencia e o caminho mais direto e ja validado para levantar o teto val/test em direcao ao piso da RFC, priorizando a categoria mais rara do corpus (preliminar, 16/16 instancias, a mais escassa entre as 24 categorias da ontologia v8)."
success_signal: "scripts/segmenter_governance_status.py mostra document_count > 96 apos o lote (idealmente +6, para ~102) e annotation_count correspondentemente maior, com pelo menos 1 novo par preliminar_inicio/preliminar_fim adicionado por documento ingerido; ruff check/format e a suite pytest do segmentador permanecem verdes; uma PR e aberta com os documentos ingeridos e o CI passa; o merge e confirmado e registrado."
---

# Goal: setimo lote real multi-tribunal para #1050

Selecionar candidatos reais e nunca usados de `data/segmenter_samples/*.jsonl`
com hit heuristico para a categoria mais rara do corpus (`preliminar`),
priorizando tribunais ja representados mas com poucos documentos
(store_count baixo) para aumentar volume, nao so diversidade de
tribunal (seguindo o `next_move` explicito da rodada anterior, la7bsl).
Anotar cada um via subagente independente com o prompt canonico
Technique 1, aplicar os pre-processamentos ja conhecidos (html.unescape,
limpador HTML->texto quando necessario) antes de atribuir a um
subagente, ingerir os que passarem na validacao mecanica/verbatim, e
corrigir a inconsistencia conhecida entre `knowledge/backlog/issue-1050.md`
e o estado real do repositorio (desatualizado desde o lote 4).
