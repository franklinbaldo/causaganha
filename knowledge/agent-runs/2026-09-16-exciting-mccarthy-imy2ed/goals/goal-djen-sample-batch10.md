---
type: AgentGoal
id: "2026-09-16-exciting-mccarthy-imy2ed-goal-djen-sample-batch10"
run_id: "2026-09-16-exciting-mccarthy-imy2ed"
statement: "Ingerir um decimo lote real de documentos DJEN nao usados (Sentenca/Acordao, categoria escassa 'preliminar') no corpus de treino do segmentador para a issue #1050, elevando document_count e o teto de val/test em scripts/segmenter_governance_status.py, sem colidir com a PR #1557 (nono lote, sessao concorrente, ainda aberta)."
motivation: "#1050 e a unica linhagem de trabalho genuinamente desbloqueada e valiosa disponivel hoje -- todo o resto do backlog (epics #1047/#1053, #950, #951, #985, #1022, #1482) esta bloqueado por GPU/humano-no-loop ou por credenciais ausentes (IA, Cloudflare), sem fato novo. #1051 (validation set independente) depende de #1050 cruzar o piso combinado de RFC 0012 Sec 5 item 4 (~200 documentos totais); document_count esta em 109 pre-lote9/10, ainda distante do piso. 'preliminar' continua a categoria mais escassa (21 instancias, contra >=10 exigido, mas a mais proxima do teto entre as 25 categorias)."
success_signal: "scripts/segmenter_governance_status.py rodado ao vivo apos a ingestao mostra document_count e annotation_count maiores que o estado pre-lote (109/162), com os novos documentos verificaveis em SegmenterDatasetStore.list_documents(). uv run pytest -q (suite completa) verde, incluindo um teste novo/estendido em tests/segmenter_dataset/test_segmenter_governance_status.py que fica RED antes da ingestao e GREEN depois. PR aberta, CI verde, mergeada."
---

# Goal: decimo lote real do corpus do segmentador (#1050)

Ver `decision-resume-under-legacy-mechanism.md` para a decisao de manter
o mecanismo AgentRun apesar da depreciacao registrada em
`.claude/hourly-loop.md`, e `reading-prs.md` para a exclusao explicita
dos IDs de documento ja reservados pela PR #1557 (sessao concorrente,
nono lote) da selecao de candidatos desta rodada.
