---
type: AgentGoal
id: "2026-09-19-exciting-mccarthy-gbf44b-goal-djen-sample-batch22"
run_id: "2026-09-19-exciting-mccarthy-gbf44b"
goal: "Ingerir vigesimo segundo lote real multi-tribunal para o corpus de treino do segmentador (#1050)"
rationale: "RFC 0012 Sec 5 item 4 exige piso >=30 documentos adjudicados em val e >=30 em test. O corpus real (document_count=167, val_ceiling=test_ceiling=25, ambos confirmados ao vivo via scripts/segmenter_governance_status.py nesta rodada) ainda esta abaixo desse piso -- o teto so alcanca 30/30 com document_count>=~200. 21 lotes anteriores ja provaram que scripts/ingest_djen_sample_technique1_batch.py escala sem mudanca de codigo de producao. Nenhuma outra issue aberta oferece caminho de execucao imediato sem bloqueio de credenciais externas (confirmado nas leituras desta rodada: #1482 bloqueada em deploy Cloudflare, #1468-1472 bloqueadas em credenciais IA)."
success_signal: "scripts/segmenter_governance_status.py mostra document_count > 167 apos o lote, com annotation_count correspondentemente maior; uv run ruff check/format e a suite pytest do segmentador permanecem verdes; uma PR e aberta com os documentos ingeridos e o CI passa; o merge e confirmado e registrado; knowledge/backlog/issue-1050.md atualizado com os numeros e qualquer nova classe de risco encontrada."
status: "achieved"
---

# Goal: vigesimo segundo lote real multi-tribunal para #1050

Escanear ao vivo `data/segmenter_samples/*.jsonl` (campos corretos
`text`/`info.id`/`info.tribunal`/`info.tipoDocumento`), excluir
candidatos ja no store (por `(tribunal, id)` derivado do nome do
arquivo, nao do campo `info.tribunal` que pode estar vazio -- classe de
risco 11), e selecionar ~6 candidatos reais nunca usados nos tribunais
de menor `store_count` (continuando a estrategia de volume estabelecida
desde o lote 9). Limpar HTML bruto/entidades quando o tribunal
escolhido tiver esse padrao conhecido (TJGO, TRF2, etc). Anotar cada um
via subagente independente com o prompt canonico Technique 1
(`data/segmenter_splits/technique1_annotation_prompt.md`), verificar
fidelidade verbatim byte-a-byte antes de ingerir via
`scripts/ingest_djen_sample_technique1_batch.py`, e atualizar
`knowledge/backlog/issue-1050.md` com os numeros e qualquer achado
novo.

**Alcancado**: document_count 167->173, val_ceiling/test_ceiling
25/25->26/26. 6 documentos (TJGO/543564741, TJPB/578900185,
TJPA/576803379, TJPA/576805366, TJRJ/327508788, TJTO/285747298)
ingeridos apos corrigir 2 defeitos de transcricao (NBSP, `&` nao
escapado) e declarar 3 overrides verificados contra o texto-fonte.
Um novo falso positivo do audit semantico foi triado e o allowlist do
teste de regressao correspondente foi estendido com uma razao
documentada.
