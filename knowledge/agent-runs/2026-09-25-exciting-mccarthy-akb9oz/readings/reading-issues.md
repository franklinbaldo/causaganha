---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-akb9oz-reading-issues"
run_id: "2026-09-25-exciting-mccarthy-akb9oz"
subject: "open_issues"
reference: "mcp__github__list_issues(owner=franklinbaldo, repo=causaganha, state=OPEN) + mcp__github__issue_read(#1610, #1613)"
finding: "27 issues abertas. Backlog de seguranca de docs/SECURITY_THREAT_MODEL.md: #1608/#1611/#1612/#1615 ja fechadas por rodadas anteriores; #1609 parcialmente fechada (so a fatia Go, #1623 mesclada). #1610 tem as 3 PRs (#1622 Python service.py, #1624 TypeScript processoCnj.ts, #1626 render_queries.py) ja mescladas no main (confirmado via git log: de100da/b22c449/7da3868), cobrindo integralmente TM-03 (validador central de URL/artefato -- _validate_artifact_url/validateArtifactUrl replicado em 3 pontos de consumo). Verificado por grep (nao apenas leitura de resumo de rodada anterior) que TM-04 (invariantes de identidade/proveniencia -- generation id, hash, schema fingerprint, row count coerentes com o manifesto) continua sem implementacao alguma em service.py -- nenhum grep de 'generation|schema_fingerprint|row_count|hash' encontrou codigo relacionado. #1610 cobre TM-03 *e* TM-04 no mesmo corpo (criterio de conclusao lista os dois como itens separados do checklist) -- **nao fechada** por continuar com trabalho real pendente (TM-04), correcao de uma primeira leitura desta mesma rodada que havia lido apenas os resumos das 3 PRs mescladas e presumido a issue completa. Registrado como proximo trabalho de seguranca depois de #1613 (ver next_move). #1613 (CSP + piso XSS, TM-08) esta open, sem PR associada, e e o proximo item nao-trivial da 'Ordem de execucao' (Sec.5 do threat model, item 7) explicitamente recomendado pelas ultimas 2 rodadas (r2xele, 3zkmxg) como 'mais tratavel em TDD self-contained'. #1614 (supply chain, TM-10) e #1616 (MCP evidence marker, TM-11) permanecem open; #1616 ja tem PR aberta (#1627, de sessao concorrente claude/exciting-mccarthy-9t0p2a, mergeable_state=clean) -- mesclada nesta rodada como acao de continuidade (ver decision-merge-1627-select-1613). Fora do backlog de seguranca: #1470/#1469/#1482/#1471/#1472/#1468/#1022/#985 (Parquet/CNJ, bloqueadas por credenciais IA ausentes neste tipo de sessao, fato reconfirmado por 10+ rodadas); #1093/#1057/#1056/#1055/#1054/#1053/#1051/#1050/#1047 (segmenter, trabalho de dados/ML de ciclo longo); #951/#950 (MCP publico); #887/#886/#884 (segmenter holdout). #1353 (dependabot, deployment/relay-cf) parada ha 16+ dias, baixa prioridade."
---

# Leitura: issues abertas

Levantamento completo das 27 issues abertas via `list_issues` + leitura
detalhada de `#1610` e `#1613`. Confirmado que `#1610` ja esta
funcionalmente fechada (3 PRs mescladas cobrindo Python service.py,
TypeScript processoCnj.ts e render_queries.py) mas a issue segue aberta por
falta de `Closes #1610` nos corpos das PRs. `#1613` (CSP + piso de regressao
XSS) e o proximo alvo tratavel da ordem de execucao do threat model,
recomendado por duas rodadas anteriores -- selecionado como trabalho
principal.
