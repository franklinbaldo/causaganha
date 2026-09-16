---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-5ov0kv-reading-issues"
run_id: "2026-09-15-exciting-mccarthy-5ov0kv"
subject: "open_issues"
reference: "mcp__github__list_issues(owner=franklinbaldo, repo=causaganha, state=OPEN, orderBy=UPDATED_AT desc)"
finding: "22 issues abertas, mesmo conjunto das ultimas rodadas de hoje. #1051 (validation set independente do segmentador, filha de #1047) segue sendo a unica frente de dominio real, desbloqueada e nao esgotada. #1468-#1472 (Parquet/CNJ) e #1482 (proxy CORS do archive.org) permanecem esgotados no que nao depende de credenciais IA/Cloudflare ausentes deste ambiente. Demais issues (#950/#951/#1093/#1022/#985, cluster #884/#886/#887/#1047/#1053-1057) seguem gated por infra GPU/deploy/dados que este ambiente nao tem."
---

# Leitura: issues abertas

`mcp__github__list_issues` (22 issues abertas). Verificado ao vivo com `uv
run python scripts/segmenter_governance_status.py --store data/segmenter`:
document_count=61, annotation_count=98, review_count=23,
evaluation_eligible_count=23 no momento desta leitura (antes de descobrir e
mesclar a PR concorrente #1527, ver reading-prs). Inventario ad-hoc contra
`SegmenterDatasetStore` confirmou 21 documentos com exatamente uma
anotacao unseeded e nenhuma review -- candidatos genuinos a uma segunda
anotacao Tecnica 1, rumo a meta de RFC 0012 Sec 5.4 (>=30 val + >=30 test).
