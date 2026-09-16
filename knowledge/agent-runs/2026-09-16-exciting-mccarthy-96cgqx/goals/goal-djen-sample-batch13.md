---
type: AgentGoal
id: "2026-09-16-exciting-mccarthy-96cgqx-goal-djen-sample-batch13"
run_id: "2026-09-16-exciting-mccarthy-96cgqx"
goal: "Ingerir o decimo terceiro lote real multi-tribunal para o corpus de treino do segmentador (#1050)"
rationale: "RFC 0012 Sec 5 item 4 exige piso >=30 documentos adjudicados em val e >=30 em test; document_count=121 e val_ceiling=test_ceiling=18 (verificado ao vivo via scripts/segmenter_governance_status.py no inicio da rodada), ainda muito abaixo do piso. Doze lotes anteriores ja provaram scripts/ingest_djen_sample_technique1_batch.py estavel sem mudanca de codigo de producao na maioria deles; a mineracao por diversidade de tribunal e pela categoria rara preliminar estao esgotadas (confirmado por lotes 11/12) -- o caminho e volume em tribunais ja representados, priorizando o menor store_count."
success_signal: "scripts/segmenter_governance_status.py mostra document_count > 121 apos o lote, com annotation_count correspondentemente maior; nenhum documento novo e uma duplicata de conteudo/de (tribunal, id_documento) ja existente (verificado via git status --short data/segmenter e checagem direta do document_id contra o store); ruff check/format e a suite pytest do segmentador permanecem verdes; uma PR e aberta com os documentos ingeridos, o CI passa, e o merge e confirmado e registrado nesta rodada ou explicitamente deixado para a proxima."
status: "achieved"
---

# Goal: decimo terceiro lote real multi-tribunal para #1050

Escanear ao vivo `data/segmenter_samples/*.jsonl` (excluindo TJRO,
excluindo arquivos auxiliares `*_annotation_gold`/`*_annotation_raw`,
filtro de 2500-18000 caracteres, tipoDocumento Sentenca/Acordao),
deduplicar contra o store atual usando `content_hash(text)` e
`(tribunal, id_documento)` (nao o `sha256` do campo `info`, que e um
espaco de hash diferente -- classe de risco 9 do backlog), priorizando
tribunais ja representados com o menor `store_count` (TJRJ, TJSE, TJMG,
TRF5, TJRS, TRF2, TJTO, por ordem do backlog). Pre-processar defeitos
conhecidos (html.unescape, limpador HTML->texto, normalizacao CRLF->LF,
substituicao de caracteres de controle) antes de atribuir a subagentes.
Anotar via subagentes independentes com o prompt canonico Technique 1,
gravando a saida tagueada em diretorio separado do texto-fonte (classe
de risco 10). Ingerir via `scripts/ingest_djen_sample_technique1_batch.py`,
verificar cada `document_id` retornado contra o store real e o conteudo
de cada anotacao antes de confiar na mensagem de sucesso do script.
Atualizar `knowledge/backlog/issue-1050.md` com os numeros reais do
lote 13.
