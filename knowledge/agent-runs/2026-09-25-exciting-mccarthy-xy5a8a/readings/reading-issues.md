---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-xy5a8a-reading-issues"
run_id: "2026-09-25-exciting-mccarthy-xy5a8a"
subject: "open_issues"
reference: "GitHub issues abertas, franklinbaldo/causaganha (list_issues, state=OPEN, 24 abertas)"
finding: "Backlog de seguranca de docs/SECURITY_THREAT_MODEL.md reduzido a 3 issues abertas: #1610 (validar URLs de manifesto/proveniencia -- ja fechado em fatias Python/TS por rodadas anteriores, item 'nenhum read_parquet sem validacao' ainda com pontas soltas como DuckDBExplorer.svelte), #1614 (supply chain Python/container -- ultima fatia, SBOM+scan, coberta pela PR aberta #1640 ainda em CI), #1616 (marcar texto judicial como evidencia nao-confiavel no MCP -- PR #1627 fechou o nucleo para publicacoes_buscar/decisoes_buscar mas deixou processo_consultar (DocumentoResult.resumo, StjAcordaoResult.tese/ementa) explicitamente como follow-up, documentado na propria PR e no TM-11 da matriz de ameacas). #1616 selecionada como trabalho principal: self-contained, TDD puro, sem credenciais externas nem decisao de politica de deploy, com precedente direto e testado no proprio repositorio (o mesmo padrao Literal+Field ja usado em publicacoes.py/decisoes.py). Demais 21 issues abertas sao trilhas de longo prazo sem gate automatizado de rodada unica: Parquet/CNJ (#1470/#1469/#1482/#1471/#1472/#1468/#1022/#985) bloqueadas por credenciais IA ausentes neste tipo de sessao (fato ja estabelecido por 10+ rodadas anteriores); segmenter (#1050/#1051/#1057/#1056/#1055/#1054/#1047/#1053/#884/#887/#886) sao ciclos continuos de anotacao/treino, ja com PR aberta (#1605, bloqueada); #951/#1093 sao produto de longo prazo sem TDD gate imediato."
---

# Leitura: issues abertas

24 issues abertas revisadas via `list_issues`. O backlog de seguranca
operacional continua o mais tratavel por TDD em uma rodada unica; `#1616`
tem seu nucleo ja fechado (PR #1627) com um follow-up explicito e
delimitado (`processo_consultar`) -- selecionada como trabalho principal
desta rodada por continuidade direta com o padrao ja estabelecido.
