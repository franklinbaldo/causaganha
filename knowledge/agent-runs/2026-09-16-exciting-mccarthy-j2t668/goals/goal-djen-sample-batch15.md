---
type: AgentGoal
id: "2026-09-16-exciting-mccarthy-j2t668-goal-djen-sample-batch15"
run_id: "2026-09-16-exciting-mccarthy-j2t668"
goal: "Ingerir decimo quinto lote real multi-tribunal para o corpus de treino do segmentador (#1050)"
rationale: "RFC 0012 Sec 5 item 4 exige piso >=30 documentos adjudicados em val e >=30 em test; o corpus real (document_count=126, val_ceiling=test_ceiling=19, ambos verificados ao vivo) ainda esta abaixo desse piso. 14 lotes anteriores ja provaram que scripts/ingest_djen_sample_technique1_batch.py escala sem mudanca de codigo de producao. Um scan ao vivo desta rodada (corrigindo nomes de campo -- text/info.id, nao texto_limpo/id_documento) encontrou 218 candidatos reais elegiveis e nunca usados, concentrados nos tribunais de menor store_count (TST, TJRJ, TJTO, TRF2, todos em 2), confirmando que continuar a cadencia de crescimento de volume (nao diversidade de tribunal, que esta perto de esgotar so para TRF6/TJSC) e o caminho mais direto para levantar o teto val/test em direcao ao piso RFC."
success_signal: "scripts/segmenter_governance_status.py mostra document_count > 126 apos o lote, com annotation_count correspondentemente maior; uv run ruff check/format e a suite pytest do segmentador permanecem verdes; uma PR e aberta com os documentos ingeridos e o CI passa; o merge e confirmado e registrado; knowledge/backlog/issue-1050.md atualizado com os numeros e qualquer nova classe de risco encontrada."
status: "achieved"
---

# Goal: decimo quinto lote real multi-tribunal para #1050

Selecionar 6 candidatos reais e nunca usados de `data/segmenter_samples/*.jsonl`
nos tribunais de menor `store_count` ja representados (TST, TJRJ x2,
TJTO x2, TRF2), priorizando volume sobre diversidade de tribunal nova
(seguindo o `next_move` explicito da rodada anterior, zrek2s). Todos os
4 candidatos com markup HTML bruto embutido (TST, TJTO x2, TRF2) foram
limpos com o limpador ja validado
`docs/planning/evidence/segmenter-djen-sample-batch3-clean-html.py`
antes da anotacao. Anotar cada um via subagente independente com o
prompt canonico Technique 1, ingerir os que passarem na validacao
mecanica/verbatim via `scripts/ingest_djen_sample_technique1_batch.py`,
e corrigir `knowledge/backlog/issue-1050.md` com os numeros e qualquer
achado novo.

**Alcancado**: document_count 126->132 (+6), val_ceiling/test_ceiling
19->20, alem de uma tecnica nova (correcao programatica de NBSP
pervasivo via diff-e-remapeamento) e uma correcao de framing sobre o
estado real do pool (218 candidatos elegiveis, nao "quase esgotado").
