---
type: AgentGoal
id: "2026-09-20-exciting-mccarthy-fv62kx-goal-djen-sample-batch24"
run_id: "2026-09-20-exciting-mccarthy-fv62kx"
goal: "Ingerir vigesimo quarto lote real multi-tribunal para o corpus de treino do segmentador (#1050)"
rationale: "RFC 0012 Sec 5 item 4 exige piso >=30 documentos adjudicados em val e >=30 em test. O corpus real (document_count=179, val_ceiling=test_ceiling=27, confirmados ao vivo via scripts/segmenter_governance_status.py nesta rodada) ainda esta abaixo desse piso. 23 lotes anteriores ja provaram que scripts/ingest_djen_sample_technique1_batch.py escala sem mudanca de codigo de producao. Nenhuma outra issue aberta oferece caminho de execucao imediato sem bloqueio de credenciais externas ou duplicacao de esforco de sessao concorrente (confirmado nas leituras desta rodada)."
success_signal: "scripts/segmenter_governance_status.py mostra document_count > 179 apos o lote, com annotation_count correspondentemente maior; uv run ruff check/format e a suite pytest do segmentador permanecem verdes; uma PR e aberta com os documentos ingeridos e o CI passa; o merge e confirmado e registrado; knowledge/backlog/issue-1050.md atualizado com os numeros e qualquer nova classe de risco encontrada."
status: "achieved"
---

# Goal: vigesimo quarto lote real multi-tribunal para #1050

Escanear ao vivo `data/segmenter_samples/*.jsonl` (campos corretos
`text`/`info.id`/`info.tribunal`/`info.tipoDocumento`), excluir
candidatos ja no store (por `(tribunal, id)` derivado do nome do
arquivo, nao do campo `info.tribunal` que pode estar vazio -- classe de
risco 11), e selecionar ~6 candidatos reais nunca usados nos tribunais
de menor `store_count`. Limpar HTML bruto/entidades quando o tribunal
escolhido tiver esse padrao conhecido. Anotar cada um via subagente
independente com o prompt canonico Technique 1
(`data/segmenter_splits/technique1_annotation_prompt.md`), verificar
fidelidade verbatim byte-a-byte antes de ingerir via
`scripts/ingest_djen_sample_technique1_batch.py`, e atualizar
`knowledge/backlog/issue-1050.md` com os numeros e qualquer achado
novo.

**Alcançado**: document_count 179->185, val_ceiling/test_ceiling
27/27->28/28. 6 documentos (TJBA/574460088, TJMA/42725100,
TJPI/22443826, TJES/577051509, TJGO/543517919, TJPB/578906897)
ingeridos com fidelidade verbatim confirmada na primeira tentativa
(nenhum defeito de transcrição encontrado) e 7 overrides
`--allowed-unmatched-overrides` declarados, todos verificados contra o
texto-fonte bruto. `uv run pytest -q tests/segmenter_dataset`: 208
passed. Zero achados semânticos novos.
