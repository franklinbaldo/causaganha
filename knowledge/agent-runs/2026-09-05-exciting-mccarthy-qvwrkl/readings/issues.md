---
type: AgentReading
id: "2026-09-05-exciting-mccarthy-qvwrkl-reading-issues"
run_id: "2026-09-05-exciting-mccarthy-qvwrkl"
subject: "open_issues"
reference: "franklinbaldo/causaganha open issues (list_issues, state=OPEN, 32 total, checked 2026-09-05T16:2x)"
finding: "#1135 (web(proveniencia): oferecer ação consistente de copiar referência verificável) remains open with closed_by_pull_requests empty: PR #1148 (merged by the immediately preceding round, commit bbc6c85) delivered only the first acceptance-criterion slice (dossier + per-document 'Copiar referência' on /processo). Its own recorded next_move explicitly names the second slice as unfinished: 'extend the same action to /publicacoes results ... reusing buildDocumentoReferenceText's shape where the publication row carries a public origin URL' — one of #1135's own acceptance criteria ('ação disponível em /processo e resultados de /publicacoes onde houver provenance') is still unmet. Three other issues (#1138 sitemap, #1139 processo hierarchy, #1145 mcp job routing) already have open, stacked PRs (#1150/#1151/#1152, see PR reading) opened by a separate concurrent process in the last ~30 minutes and explicitly marked 'Do not merge in implementation phase' — picking up the same issues now would race that in-flight work. #1107 (contract(processo) MCP/Web parity) is READY but is an explicitly multi-slice fixture+parity effort too large for one autonomous round per its own 'Estado' note. #1042 (ops(catalog) prove update-catalog end-to-end) needs observing a live IA-uploading GitHub Actions run — operational, not a quick autonomous slice. #1135's second slice is therefore the best-fit unit of work: it is the named continuation of the last round's own next_move, self-contained to the web frontend, has no external side effects, and does not touch any file the three in-flight PRs modify (sitemap.xml, ProcessoLookup layout, MCP instructions)."
---

# Leitura de issues abertas

Levantamento via `list_issues`. Achado central: #1135 tem uma segunda fatia explicitamente pendente (superfície `/publicacoes`), nomeada como `next_move` da rodada anterior, e não colide com as três PRs empilhadas já abertas por outro processo para #1138/#1139/#1145.
