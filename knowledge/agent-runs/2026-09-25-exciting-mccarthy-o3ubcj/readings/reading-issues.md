---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-o3ubcj-reading-issues"
run_id: "2026-09-25-exciting-mccarthy-o3ubcj"
subject: "open_issues"
reference: "GitHub issues abertas (franklinbaldo/causaganha, mcp__github__list_issues, state=OPEN, 25 abertas)"
finding: "Cluster de segurança #1608-#1616: apenas #1610 (TM-04) e #1609/#1614 (infra/deploy) seguem listados como abertos; #1608/#1611/#1612/#1613/#1615/#1616 já fechados por dezenas de rodadas anteriores. #1610/TM-04 tinha, até esta rodada, a checagem de tribunal e a de rodapé KV_METADATA (item_id/schema_version) fechadas SÓ do lado Python (service.py), com o lado Web (web/src/lib/processoCnj.ts) explicitamente marcado como follow-up pendente em comentário de código e no próprio TM-04 do SECURITY_THREAT_MODEL.md -- confirmado por leitura direta do arquivo antes de qualquer trabalho começar. #1609 (relay) tinha a fatia Go (#1623) e a fatia Python (#1625) já mescladas; restava a fatia Cloudflare (branch akb9oz->PR #1634, ver leitura de PRs). #1614 (supply chain Python/container) já fechado por rodada anterior (06279ed). Fora do cluster de segurança: clusters #1468-1472 (Parquet/CNJ) e #1482 (CORS) seguem bloqueados por credenciais IA/Cloudflare ausentes nesta sessão -- confirmado por dezenas de rodadas anteriores, não reinvestigado nesta rodada por não ter mudado. Cluster #1047-1057/#884/#886/#887 (segmenter RFC 0012) é a frente historicamente mais ativa (issue #1050 com 27+ batches ingeridos) mas não foi a escolhida nesta rodada -- ver goal e decision para o porquê."
---

# Leitura: issues abertas
