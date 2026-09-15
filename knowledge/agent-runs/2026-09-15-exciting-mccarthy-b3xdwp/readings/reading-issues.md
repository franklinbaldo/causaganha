---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-b3xdwp-reading-issues"
run_id: "2026-09-15-exciting-mccarthy-b3xdwp"
subject: "open_issues"
reference: "mcp__github__list_issues franklinbaldo/causaganha state=OPEN orderBy=UPDATED_AT DESC (22 abertas no total)"
finding: "#1051 (dataset de validação independente do segmentador, RFC 0012) continua sendo a issue aberta mais recentemente atualizada (2026-09-15T08:56:06Z), atualizada pela sequência de merges de hoje (PRs até #1513). Cluster Parquet/CNJ (#1469/#1470/#1482/#1471/#1472/#1468) ocupa as próximas posições, todas girando em torno da mesma dependência: #1472 (publicação real da regeneração no Internet Archive) segue bloqueada por falta de IA_ACCESS_KEY/IA_SECRET_KEY -- confirmado ao vivo nesta rodada (env vazio). Nenhuma issue nova de domínio apareceu desde a última rodada (2cjjig, terminada 12:42:24Z)."
---

# Leitura: issues abertas

Mesma leitura da linhagem de hoje: `env | grep -iE 'IA_|ARCHIVE|CLOUDFLARE|GCP|CLOUDSDK'`
mostra só variáveis CLOUDSDK_* de boilerplate de proxy (sem credenciais reais
de projeto), então o cluster Parquet/CNJ que depende de publicação real no
Internet Archive (#1472, e por extensão #1468/#1470/#1471) permanece
bloqueado, sem novidade desde 11/09. #1051 é a única frente de domínio
aberta, desbloqueada e ainda não esgotada
(`uv run python scripts/segmenter_governance_status.py`: review_count=13
contra meta de ~60 do RFC 0012 §5.4).
