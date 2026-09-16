---
type: AgentReading
id: "2026-09-16-exciting-mccarthy-imy2ed-reading-issues"
run_id: "2026-09-16-exciting-mccarthy-imy2ed"
subject: "open_issues"
reference: "https://github.com/franklinbaldo/causaganha/issues/1050, https://github.com/franklinbaldo/causaganha/issues/1051, https://github.com/franklinbaldo/causaganha/issues/1482"
finding: "list_issues (22 abertas) confirma que a linhagem ativa continua #1050 (repair/scale real training corpus, filha de #1047) e #1051 (validation set independente, bloqueada por design ate #1050 levantar o teto proximo de ~200 documentos). Nesta mesma data (2026-09-16), 9 rodadas concorrentes ja levaram document_count de 61 para 109 confirmados em main (mais um 9o lote de 6 documentos, PR #1557, aberto ha poucos minutos e ainda com CI pendente). Quase todo o resto do backlog (issue-1047, issue-1053, issue-950, issue-951, issue-985, issue-1022) esta 'blocked' por GPU/humano-no-loop ou por credenciais IA ausentes, sem fato novo desde a ultima verificacao (2026-09-07 ou 2026-09-11). Issue #1482 (CORS do endpoint de download do archive.org bloqueando DuckDBExplorer.read_parquet no browser) tem 2 comentarios: a confirmacao real-browser ja foi feita, e o workaround (Cloudflare Worker) ja foi implementado e mesclado em PR #1521, mas nao pode ser implantado porque nenhuma sessao tem credenciais Cloudflare -- tambem bloqueada por credencial ausente, sem novidade."
---

# Leitura: issues abertas

`list_issues(state=OPEN, orderBy=UPDATED_AT desc)` retornou 22 issues.
Confirmei que a unica linhagem genuinamente desbloqueada e ativa hoje e
#1050 (mineracao real de corpus para o segmentador), com #1051 dependente
dela. Inspecionei tambem #1482 (`issue_read` + `get_comments`) porque
parecia um candidato alternativo nao tocado pela mineracao de hoje --
mas seus proprios comentarios mostram que o trabalho de codigo ja foi
feito (PR #1521 mesclada) e o unico passo restante (`wrangler deploy`)
exige credenciais Cloudflare que esta sessao nao tem, entao nao e um
caminho acionavel nesta rodada. As demais issues do backlog seguem
bloqueadas pelos mesmos motivos ja documentados (GPU/humano-no-loop,
IA_ACCESS_KEY/IA_SECRET_KEY ausentes), sem fato novo.
