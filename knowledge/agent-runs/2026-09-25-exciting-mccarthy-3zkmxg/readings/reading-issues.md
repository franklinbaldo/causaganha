---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-3zkmxg-reading-issues"
run_id: "2026-09-25-exciting-mccarthy-3zkmxg"
subject: "open_issues"
reference: "franklinbaldo/causaganha issues (list_issues, state=OPEN, 28 total, orderBy created_at desc); issue_read #1609, #1611"
finding: "28 issues abertas. O backlog de seguranca gerado por #1617 (docs/SECURITY_THREAT_MODEL.md, mesclada em 2026-09-24) tem 3 issues ja fechadas por rodadas anteriores da mesma janela (#1608 eval/eliminacao de eval no workflow, #1612 formula injection CSV, #1615 allowlist de tribunal DataJud) e 6 ainda abertas: #1609 (relay/DJEN proxy egress), #1610 (boundary de URLs de manifesto + identidade de geracao), #1611 (budgets de ingestao contra ZIP/JSON/download bombs), #1613 (CSP + piso XSS), #1614 (supply chain: lock/build/container/SBOM), #1616 (contrato MCP de conteudo nao confiavel). A ordem sugerida por docs/SECURITY_THREAT_MODEL.md Sec.5 coloca #1609 antes de #1611, mas #1609 abrange 3 superficies heterogeneas (relay Python, relay Cloudflare em JS, djen_proxy.go) sem fixture sintetica pronta, enquanto #1611 e self-contained em um unico modulo Python (src/causaganha/consolidate/zip_processor.py + download_zip), sem credenciais externas, com gate automatizado explicito no corpo da issue (ZIPs sinteticos: many-members, membro acima do limite, alta razao de compressao, JSON individual grande, path traversal, download acima do teto) -- mesmo padrao de tratabilidade que fez #1612/#1615 serem escolhidas em rodadas anteriores da mesma janela. Selecionada como trabalho principal desta rodada. #1470/#1469/#1482/#1471/#1472/#1468/#1022/#985 (Parquet/CNJ) seguem bloqueadas por credenciais Internet Archive ausentes neste tipo de sessao, fato ja estabelecido por 9+ rodadas anteriores -- nao reprovado ao vivo aqui por falta de fato novo. #1050 (corpus real do segmentador) segue como lineage ativa, mas com PR concorrente (#1605, batch27) em conflito de merge numa branch que esta sessao nao pode editar -- ver reading-prs."
---

# Leitura: issues abertas

Releu a lista completa de issues abertas (28 no total) e o corpo integral
de `#1609` e `#1611`. O backlog de seguranca da matriz operacional
(`docs/SECURITY_THREAT_MODEL.md`, PR `#1617` mesclada na janela anterior)
ja teve 3 de 9 issues fechadas por rodadas anteriores (`#1608`, `#1612`,
`#1615`). Das 6 restantes, `#1611` (budgets de ingestao contra ZIP/JSON/
download bombs) e a mais tratavel em uma unica rodada: self-contained,
sem credenciais, gate automatizado ja especificado no corpo da issue,
mesmo padrao que fez `#1612`/`#1615` serem escolhidas anteriormente.
Selecionada como trabalho principal.
