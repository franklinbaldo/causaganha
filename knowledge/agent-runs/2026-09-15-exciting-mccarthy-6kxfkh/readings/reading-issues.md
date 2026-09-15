---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-6kxfkh-reading-issues"
run_id: "2026-09-15-exciting-mccarthy-6kxfkh"
subject: "open_issues"
reference: "mcp__github__list_issues(owner=franklinbaldo, repo=causaganha, state=OPEN) via subagent; uv run python scripts/segmenter_governance_status.py; inventario ao vivo do pool de candidatos"
finding: "22 issues abertas. Cluster Parquet/CNJ (#1468-1472) e o proxy CORS do archive.org (#1482) seguem esgotados no que nao depende de credenciais IA/Cloudflare ausentes deste ambiente -- #1482 permanece aberta apesar de PR #1521 (merged) ja ter corrigido o sintoma via proxy, resta so confirmacao com deploy real. #1051 (validation set independente do segmentador, filha de #1047) e a unica frente de dominio real, desbloqueada e nao esgotada: governance_status ao vivo mostra document_count=61, annotation_count=96, review_count=21, evaluation_eligible_count=21 -- exatamente o after-state deixado pela rodada anterior (pxa8pi), confirmando continuidade sem gap. Inventario ao vivo (script ad-hoc contra SegmenterDatasetStore) confirma pool de 23 documentos com exatamente uma anotacao unseeded e nenhuma review (25 -> 23 apos os 2 tocados por pxa8pi), candidatos genuinos a uma segunda anotacao. Restante do backlog (#950/#951/#1093/#1022/#985, cluster #884/#886/#887/#1053-1057) segue gated por infra GPU/deploy/dados ausentes deste ambiente."
---

# Leitura: issues abertas

Delegado a um subagente de pesquisa (mcp__github__list_issues +
list_pull_requests, somente leitura) para levantar o estado completo de
issues e PRs sem gastar contexto local com paginacao. Resultado
cross-checado ao vivo com `uv run python scripts/segmenter_governance_status.py`
(document_count=61, annotation_count=96, review_count=21,
evaluation_eligible_count=21) e com um inventario python ad-hoc contra
`SegmenterDatasetStore` que recalculou o pool de candidatos (documentos com
exatamente uma anotacao `seeded_with="none"` e nenhuma review): 23
documentos, confirmando a reducao de 25 (inicio de pxa8pi) para 23 (apos os
2 documentos que pxa8pi levou a review). Nenhum gap de continuidade entre
rodadas.
