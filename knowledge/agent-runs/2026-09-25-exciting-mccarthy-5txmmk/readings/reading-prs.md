---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-5txmmk-reading-prs"
run_id: "2026-09-25-exciting-mccarthy-5txmmk"
subject: "open_prs"
reference: "https://github.com/franklinbaldo/causaganha/pulls?q=is%3Apr+is%3Aopen"
finding: "5 PRs abertas. #1653 (docs(knowledge): close out ...-r0zxiq) e branch de outra sessao concorrente (claude/exciting-mccarthy-r0zxiq != a branch desta sessao) -- nao assumida, por padrao ja estabelecido de nao competir por push/merge em branch alheia. #1353 (dependabot bump @vitest/mocker) e mecanica, sem sinal de bloqueio, deixada para o fluxo normal de dependabot. #1643/#1644/#1645 sao PRs externas do bot codex (branches codex/2026-09-25/*) propondo fixes de seguranca adjacentes a #1652: #1643 e #1644 tem sha/branch que parecem sobrepor as superficies 1 e 2 de #1652 (ja corrigidas nesta base por PRs internas #1654/#1657) -- provavelmente obsoletas contra o main atual, nao investigadas a fundo por nao serem o item 3 (o gap ainda aberto). #1645 (fix(reconcile): authenticate Internet Archive source files) e a mais relevante: propoe um manifesto JSON estatico com digest SHA-256 por arquivo (config/reconcile-remote-sources.json) para JURIS/DataJud, mas (a) esta desatualizada contra main (baseada em _discover_juris_items pre-#1657, que ainda usava advancedsearch.php), CI pending/0 status; (b) o desenho de manifesto vazio-por-padrao quebraria a reconciliacao em producao ate um operador popular manualmente o digest de cada arquivo, o que contradiz o pipeline de crawl continuo do projeto (arquivos novos a cada execucao). Nao adotada como base; usada apenas como leitura de contexto do gap. Investigacao no codigo (ver decision-identity-metadata-not-digest-manifest) revelou que o projeto ja tem um mecanismo de identidade auto-verificavel construido nesta mesma sessao de trabalho recente (TM-04, PRs #1648/#1650/#1651) -- KV_METADATA no rodape do proprio Parquet, gravado pelo pipeline de escrita e ja lido no lado de consulta (causaganha.processos.service._validar_metadata_juris/_validar_metadata_datajud) -- mas nunca aplicado no lado de ingestao (reconcile_processos.py), que e exatamente a superficie que #1652 item 3 aponta como faltando verificacao. Esse mecanismo, ja estabelecido e auto-suficiente (nao exige manifesto externo hand-maintained), foi escolhido como a solucao para o item 3 desta rodada."
---

# Leitura: PRs abertas

Listagem completa via GitHub MCP (`list_pull_requests`, `state=open`).
Diff completo lido para #1645 (`pull_request_read` method=get_diff) por
ser a única candidata relevante ao item 3 de #1652. Corpo completo lido
para #1653 e #1646 (já mesclada, referenciada pelo checklist de #1652)
para reconstruir a linha do tempo de #1610/#1652/TM-16 nesta mesma data.
