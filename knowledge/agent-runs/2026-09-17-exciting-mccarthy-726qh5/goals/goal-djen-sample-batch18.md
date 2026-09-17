---
type: AgentGoal
id: "2026-09-17-exciting-mccarthy-726qh5-goal-djen-sample-batch18"
run_id: "2026-09-17-exciting-mccarthy-726qh5"
goal: "Ingerir decimo oitavo lote real multi-tribunal para o corpus de treino do segmentador (#1050), sem colidir com o lote 17 concorrente (PR #1574, ainda aberta)"
rationale: "RFC 0012 Sec 5 item 4 exige piso >=30 documentos adjudicados em val e >=30 em test; scripts/segmenter_governance_status.py confirmado ao vivo nesta rodada mostra document_count=138, val_ceiling=test_ceiling=21, ainda abaixo do piso. Das 22 issues abertas, #1050 e a unica sem bloqueio externo (credenciais IA/Cloudflare ausentes bloqueiam todas as outras). Um scan ao vivo do pool de candidatos, excluindo os 6 IDs ja consumidos por PR #1574, encontrou 13-22 candidatos elegiveis em TJRR/TRF2/TJMT/TRF3/TRF5 (tribunais no tier store_count=3 nao tocados por #1574)."
success_signal: "scripts/segmenter_governance_status.py mostra document_count > 138 apos o lote, com annotation_count correspondentemente maior; uv run ruff check/format e a suite pytest do segmentador permanecem verdes; uma PR e aberta com os documentos ingeridos e nao reusa nenhum dos 6 document_id ja consumidos por PR #1574; knowledge/backlog/issue-1050.md atualizado com os numeros do lote e qualquer classe de risco nova."
status: "achieved"
---

# Goal: decimo oitavo lote real multi-tribunal para #1050

Selecionar 6 candidatos reais e nunca usados de `data/segmenter_samples/*.jsonl`,
todos sem markup HTML bruto/entidades/NBSP/caracteres de controle (todas as
quatro classes de risco de limpeza ja documentadas verificadas e limpas de
saida, evitando a necessidade de qualquer limpeza manual nesta rodada):

- TJMT/74430633 (Sentenca, 5281 chars)
- TJRR/568209392 (Sentenca, 16628 chars)
- TJRR/568328945 (Sentenca, 6385 chars)
- TRF3/42490599 (Sentenca, 10785 chars)
- TRF5/349186353 (Sentenca, 6024 chars)
- TRF5/463264301 (Acordao, 6235 chars)

Todos os 6 tribunais estavam no tier `store_count=3` (empatado com o
tier mais baixo nao-esgotado, TJMG=2 mas com pool zerado -- achado novo
desta rodada) e nenhum foi tocado pelos 5 documentos + 1 candidato
descartado listados no corpo de PR #1574 (lote 17, sessao concorrente
ainda aberta). Anotar cada um via subagente independente com o prompt
canonico Technique 1 (`data/segmenter_splits/technique1_annotation_prompt.md`),
validar fidelidade verbatim + validacao mecanica, ingerir via
`scripts/ingest_djen_sample_technique1_batch.py`, e atualizar
`knowledge/backlog/issue-1050.md` com os numeros e qualquer achado novo
(incluindo TJMG como novo tribunal com pool esgotado, paralelo a
TRF6/TJSC ja documentados).

**Alcancado**: document_count 138->144, annotation_count 191->197,
val_ceiling/test_ceiling 21/21->22/22 (confirmado ao vivo via
`scripts/segmenter_governance_status.py`). Um defeito real de
fidelidade verbatim foi encontrado e corrigido (TJRR/568328945, 11
espacos ASCII isolados omitidos pelo subagente) com uma tecnica nova
de diff-and-remap generalizada. Nove overrides `--allowed-unmatched-overrides`
foram declarados e verificados contra o texto-fonte bruto. `uv run
ruff check`/`format --check` e `uv run pytest -q tests/segmenter_dataset`
100% verdes.
