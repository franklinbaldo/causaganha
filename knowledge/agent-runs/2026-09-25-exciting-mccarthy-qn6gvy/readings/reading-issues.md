---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-qn6gvy-reading-issues"
run_id: "2026-09-25-exciting-mccarthy-qn6gvy"
subject: "open_issues"
reference: "GitHub issues abertas (franklinbaldo/causaganha, mcp__github__list_issues, 25 abertas)"
finding: "Cluster de segurança #1608-#1616 quase todo fechado por 7 rodadas OKF anteriores hoje (2026-09-25): #1608/#1611/#1612/#1613/#1615/#1616 fechadas, #1609 parcialmente (falta apenas a fatia de infraestrutura de deploy CF/relay morto), #1610 parcialmente (metade URL/tribunal fechada via 3 PRs mescladas; metade generation-id/hash/schema-fingerprint/row-count segue SEM NENHUMA implementação em qualquer gerador do repositório, confirmado por grep, e classificada por 2+ rodadas anteriores como decisão de design maior demais para uma rodada self-contained). #1614 (supply chain) e a fatia remanescente de #1609 exigem infraestrutura/credenciais de deploy fora do alcance de uma sessão sem elas. Fora do cluster de segurança: #1482 (CORS archive.org/download bloqueia read_parquet no browser) já tem workaround completo implementado e mesclado (Cloudflare Worker deployment/archive-cors-proxy/, PR #1521) — só falta o deploy real, bloqueado por credenciais Cloudflare ausentes, mesma classe de bloqueio já registrada. Cluster #1468-1472 (Parquet/CNJ) segue bloqueado por credenciais IA_ACCESS_KEY/IA_SECRET_KEY. Cluster #1047-1057/#884/#886/#887 (segmenter RFC 0012) é a frente mais ativa historicamente mas já reconfirmada por dezenas de rodadas hoje/ontem."
---

# Leitura: issues abertas
