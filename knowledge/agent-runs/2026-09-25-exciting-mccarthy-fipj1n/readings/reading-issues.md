---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-fipj1n-reading-issues"
run_id: "2026-09-25-exciting-mccarthy-fipj1n"
subject: "open_issues"
reference: "GitHub issues, franklinbaldo/causaganha, state=open"
finding: "Levantamento via subagente (22 issues abertas) mais verificação direta desta sessão do backlog de segurança citado por docs/SECURITY_THREAT_MODEL.md: dos 10 IDs TM-* com issue associada (#1608/#1609/#1610/#1611/#1612/#1613/#1615/#950/#1614/#1616), apenas #1610 (validar URLs de manifesto/proveniência antes do DuckDB) permanece aberta — as outras 9 já fecharam (confirmado via mcp__github__issue_read para cada uma, não apenas lido de cache). O critério de conclusão de #1610 tem 4 itens; 3 já tinham evidência extensa de trabalho anterior (validador central de URL em Python/TS, checagem de coerência de tribunal, KV_METADATA para djen) documentada na própria matriz (TM-03/TM-04) e num handoff Wisk (.wisk/knowledge/experiences/handoffs/handoff-issue-1610-artifact-url-followup.md) que já auditou service.py, processoCnj.ts, DuckDBExplorer.svelte, render_queries.py e resolve_juris_urls_for_cnj (este último corretamente descartado: usa arquivo_ia_url só para filtro de membership Python, nunca para interpolação SQL). Esse handoff não cobriu causaganha.decisoes.published.discover_published_juris_datasets/_juris_url nem tjro_juris.manifest.ManifestJuris — investigação desta sessão achou aí um gap real e não auditado: mes_ano de um manifesto JURIS remoto (fetched via juris_archive.read_manifest_text, MANIFEST_DOWNLOAD_URL em archive.org) é interpolado sem validação em _juris_url, e como urllib.parse.quote() preserva '/' por padrão, um mes_ano malicioso como '2024-01/../../secret-item' sobrevive intacto até a URL final consumida por read_parquet([...]) em causaganha.decisoes.search — reproduzido ao vivo antes de qualquer mudança. Outros itens do backlog original (Parquet/CNJ #1470/#1469/#1471/#1472/#1468/#1022/#985, segmenter #1050 e derivadas) permanecem bloqueados por falta de credenciais Internet Archive (não disponíveis neste tipo de sessão) ou, no caso de #1605 (PR do batch27 do segmenter), por um conflito de merge real e reconfirmado (ver reading-prs)."
---

# Leitura: issues abertas

Levantamento amplo via subagente + verificação direta desta sessão do
estado do backlog de segurança citado em `docs/SECURITY_THREAT_MODEL.md`.
Apenas `#1610` segue aberta entre as 10 issues de segurança da matriz.
Investigação do seu critério de conclusão revelou um gap real e não
auditado por rodadas/handoffs anteriores: `mes_ano` de um manifesto JURIS
remoto flui sem validação até uma URL de `read_parquet`, permitindo path
traversal — selecionado como trabalho principal desta rodada.
