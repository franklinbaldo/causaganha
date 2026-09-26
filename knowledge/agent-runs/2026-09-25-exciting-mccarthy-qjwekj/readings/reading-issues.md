---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-qjwekj-reading-issues"
run_id: "2026-09-25-exciting-mccarthy-qjwekj"
subject: "open_issues"
reference: "GitHub issues abertas, franklinbaldo/causaganha (list_issues, state=OPEN, 22 abertas)"
finding: "#1610 (security(archive): validar URLs de manifestos e invariantes de proveniencia antes do DuckDB) e a unica issue de seguranca aberta na matriz TM (docs/SECURITY_THREAT_MODEL.md) -- confirmado lendo o documento inteiro: TM-01/02/08/09/12/13/14 fechadas ou risco aceito, TM-11 fechada por #1616, TM-10 fechada por #1614/#1640, TM-05/06/07/15 apontam para #1611/#950/#1615/#1608/#1609/#1614 (todas ja fechadas conforme texto do documento). TM-03 (URL de manifesto) esta 'Feito' para djen; TM-04 (identidade geracao/tribunal) documenta explicitamente 'juris/stj/datajud nao emitem esse KV_METADATA hoje -- gap real, documentado, nao coberto' -- esta e a lacuna concreta, delimitada e testavel escolhida como trabalho desta rodada (lado de escrita: tjro_juris, unico dos tres com pipeline de export Parquet sob controle deste repo -- stj_acordaos nao tem write_parquet/to_parquet em lugar nenhum). PR aberta #1646 (outra sessao, branch claude/exciting-mccarthy-fipj1n) ja fecha uma fatia adjacente e distinta de #1610/TM-03 (validacao de mes_ano contra path traversal no manifesto juris) -- verificado que nao ha sobreposicao de arquivos/linhas com o trabalho desta rodada (aquela PR toca tjro_juris/manifest.py e causaganha/decisoes/published.py; esta rodada toca so tjro_juris/service.py). #1482 (web(duckdb): archive.org download nao envia CORS) revisitada: evidencia real de navegador (docs/planning/evidence/archive-cors-probe-real-browser.json, scripts/benchmarks/archive_cors_probe.py) e degradacao 'cors-blocked' em DuckDBExplorer.svelte com testes proprios (DuckDBExplorer.cors-block-classification.test.ts) ja existem no repo, comitados por rodada(s) anterior(es) -- issue parece functionally resolvida mas segue aberta no GitHub; nao fechada nesta rodada por falta de tempo para confirmar que nao ha nenhuma ponta solta, registrada em next_move. Demais 20 issues abertas sao trilhas de longo prazo sem gate de rodada unica: Parquet/CNJ (#1470/#1469/#1471/#1472/#1468/#1022/#985) bloqueadas por credenciais IA ausentes (fato ja estabelecido por 10+ rodadas, ver knowledge/backlog/); segmenter (#1050 e derivadas #1051/#1057/#1056/#1055/#1054/#1047/#1053/#884/#887/#886) ciclo continuo de anotacao/treino com PR aberta #1605 bloqueada por conflito de merge em branch alheia (ver knowledge/backlog/issue-1050.md); #951/#1093 produto de longo prazo sem TDD gate imediato."
---

# Leitura: issues abertas

22 issues abertas revisadas via `list_issues`, cruzadas com a matriz
`docs/SECURITY_THREAT_MODEL.md` inteira. `#1610`/TM-04 documenta um gap
concreto e delimitado (juris/stj/datajud sem KV_METADATA de identidade no
rodapé Parquet) — selecionado como trabalho principal desta rodada,
restrito ao lado de escrita de `tjro_juris` para não conflitar com a PR
`#1646` (outra sessão) que toca uma fatia adjacente e distinta de
`#1610`. `#1482` parece já resolvida na prática por trabalho anterior,
mas não fechada nesta rodada por falta de confirmação final.
