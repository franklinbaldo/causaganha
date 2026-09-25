---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-9t0p2a-reading-issues"
run_id: "2026-09-25-exciting-mccarthy-9t0p2a"
subject: "open_issues"
reference: "GitHub issues abertas, franklinbaldo/causaganha (list_issues, state=OPEN, 27 abertas)"
finding: "Backlog de seguranca operacional de docs/SECURITY_THREAT_MODEL.md (#1608-#1616): #1608/#1611/#1612/#1615 ja fechadas por rodadas anteriores; #1609 (relay/DJEN proxy) e #1610 (validacao de URL de manifesto) permanecem *abertas* no GitHub apesar de commits recentes na main referenciarem ambas (2ce92d9 'security(relay): enforce HTTPS/method/header/size policy (#1609) (#1625)' e 7da3868 'security(processos): validate arquivo_ia_url in render_queries.py (#1610) (#1626)') — nenhum desses commits usou 'Closes #NNNN', entao as issues seguem abertas como guarda-chuva de fatias, nao foram fechadas automaticamente. Investigacao de codigo confirmou que o padrao de dupla-etapa (URL descoberta em um manifesto e reusada em outro read_parquet sem validacao) que #1610 mira ja esta coberto nos tres pontos identificados em rodadas anteriores (service.py, render_queries.py, processoCnj.ts); os demais usos de read_parquet no repo (candidates.py, published.py, datajud/service.py, drain.py) usam URLs de constante de modulo/config, nao valores lidos de um manifesto remoto — fora do escopo do invariante de #1610. #1613 (CSP + piso XSS) e #1614 (supply chain Python/container) permanecem abertas e sem PR em voo, mas exigem escopo maior (inventario de sinks {@html} + CSP compativel com GitHub Pages para #1613; lockfile frozen + digest de imagem + SBOM + scanner de CI para #1614) do que cabe com seguranca em uma unica rodada de TDD self-contained. #1616 (marcar texto judicial retornado pelo MCP como evidencia nao-confiavel/nao-instrucional) e Python puro, um unico modulo (src/causaganha_mcp/tools/), sem credenciais externas, sem infraestrutura de deploy, com gate automatizado explicito no corpo da issue (fixtures tipo 'ignore instrucoes anteriores' devem retornar exatamente como evidencia) — selecionada como trabalho principal desta rodada. Demais issues abertas (Parquet/CNJ #1470/#1469/#1482/#1471/#1472/#1468/#1022/#985, segmenter #1050 e derivadas, #950/#951/#1093) reconfirmadas fora de alcance pelos mesmos motivos que 10+ rodadas anteriores ja registraram (credenciais IA ausentes; PR de segmenter ja em voo em branch alheia #1605; trilhas de produto sem gate automatizado imediato)."
---

# Leitura: issues abertas

27 issues abertas revisadas via `list_issues`. Confirmado que `#1609` e
`#1610` seguem tecnicamente abertas no GitHub apesar de PRs recentes
referencia-las sem fecha-las — investigacao de codigo mostrou que o nucleo
do invariante de `#1610` (URL de manifesto validada antes de compor outro
`read_parquet`) ja esta coberto nos tres pontos relevantes do repositorio.
`#1616` (evidencia MCP nao-confiavel) selecionada como trabalho principal:
self-contained, sem infraestrutura de deploy, gate automatizado explicito.
