---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-k5wsee-reading-issues"
run_id: "2026-09-16-exciting-mccarthy-k5wsee"
subject: "open_issues"
reference: "https://github.com/franklinbaldo/causaganha/issues/1050, https://github.com/franklinbaldo/causaganha/issues/1051"
finding: "#1050 (repair/scale real training corpus) e #1051 (validation set independente) seguem abertas, ambas filhas de #1047. #1050 esta em progresso ativo ha 7 lotes reais nesta mesma data (2026-09-16): document_count subiu 61->102, val_ceiling/test_ceiling 9->15, ainda abaixo do piso de RFC 0012 Sec 5 item 4 (>=30 val, >=30 test, cada um adjudicado). #1051 permanece bloqueada por design ate #1050 levantar o teto proximo de ~200 documentos totais -- adjudicar dentro do pool atual nao pode cruzar o piso por split (verificado ao vivo na rodada c4y4rc). Nenhuma issue nova relevante foi aberta desde a ultima rodada (zrek2s, 11:47Z)."
---

# Leitura: issues abertas (#1050, #1051)

`list_issues` nao foi rodado com filtro amplo porque a linhagem ativa e
conhecida (#1050/#1051, epic pai #1047) e ja documentada em 20+ relatorios
`AgentRun` anteriores desta mesma data. Confirmei via `issue_read` que
ambas seguem `state: open`, sem edicao de corpo desde a criacao (2026-09-03),
e que os `next_move`s registrados nos relatorios recentes (la7bsl, zrek2s)
seguem validos: continuar lotes reais multi-tribunal para #1050 via
`scripts/ingest_djen_sample_technique1_batch.py`, priorizando volume em
tribunais ja representados (diversidade de tribunal esta praticamente
esgotada no pool `data/segmenter_samples/*.jsonl`).
