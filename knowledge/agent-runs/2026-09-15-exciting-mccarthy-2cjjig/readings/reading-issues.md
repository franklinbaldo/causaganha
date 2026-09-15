---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-2cjjig-reading-issues"
run_id: "2026-09-15-exciting-mccarthy-2cjjig"
subject: "open_issues"
reference: "mcp__github__list_issues franklinbaldo/causaganha state=OPEN orderBy=UPDATED_AT DESC (22 abertas no total)"
finding: "#1051 (dataset de validação independente do segmentador, RFC 0012) é a issue aberta mais recentemente atualizada (2026-09-15T08:56:06Z) -- atualizada pela própria sequência de merges de hoje (PRs #1507..#1512). O cluster Parquet/CNJ segue com #1469/#1470/#1471/#1472/#1468 entre as próximas mais atualizadas, todas girando em torno da mesma dependência: #1472 (publicação real da regeneração no Internet Archive) segue bloqueada por falta de credenciais de escrita IA_ACCESS_KEY/IA_SECRET_KEY -- confirmado ao vivo nesta rodada (env vazio). #1482 (CORS do endpoint de download do archive.org) já tem investigação registrada em rodadas anteriores (yz281l) concluindo que a alternativa s3.us.archive.org não é viável em navegador real (redirect final para host HTTP sem certificado válido). Nenhuma issue nova de domínio apareceu desde a última rodada (2jz691, 11:44 UTC)."
---

# Leitura: issues abertas

Confirma a mesma leitura da linhagem de hoje: `env | grep -i 'IA_\|ARCHIVE'`
vazio nesta sandbox, então todo o cluster Parquet/CNJ que depende de
publicação real no Internet Archive (#1472, e por extensão o fechamento
formal de #1468/#1470/#1471) permanece bloqueado, sem novidade desde
11/09. #1051 é a única frente de domínio aberta, desbloqueada e ainda não
esgotada (`uv run python scripts/segmenter_governance_status.py`:
review_count=11 contra meta de ~60 do RFC 0012 §5.4).
