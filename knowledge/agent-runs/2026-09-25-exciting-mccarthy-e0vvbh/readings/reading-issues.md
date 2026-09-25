---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-e0vvbh-reading-issues"
run_id: "2026-09-25-exciting-mccarthy-e0vvbh"
subject: "open_issues"
reference: "franklinbaldo/causaganha issues (state=open), via mcp__github__list_issues + issue_read em #1609/#1610/#1605/#1256/#1613/#1614"
finding: "27 issues abertas. As 5 issues security(...) (#1609/#1610/#1613/#1614/#1616) foram todas criadas em 2026-09-24 19:16-19:17 junto de docs/SECURITY_THREAT_MODEL.md, com ordem de execução prescrita TM-01..TM-15 no próprio documento (1608→1609→1610→1611→1615/950→1612→1613→1614→1616). No início desta rodada: #1608/#1611/#1612/#1615 já fechadas; #1616 fechada por #1627 (mergeada antes desta rodada); #1613 tinha PR #1628 aberta (mergeável, 1 check ainda em andamento) e #950 tinha PR #1629 aberta e verde -- mesclada nesta rodada como ação de continuidade (ver decision/evidence). #1610 segue aberta: a metade de política de URL já foi fechada por #1622/#1624/#1626 (Python + TypeScript); a metade de invariantes de proveniência/identidade (TM-04: 'tribunal/período/generation id/schema fingerprint/row count/hash coerentes com o manifesto') não tinha nenhuma implementação -- confirmado por leitura de #1628 (que a lista como follow-up explícito) e por investigação direta em reconcile_processos.py/service.py nesta rodada. #1605 (batch27 segmenter, branch alheia claude/exciting-mccarthy-034xwb) permanece com mergeable_state=dirty, sem comentário humano desde a criação -- reconfirmado bloqueado, não selecionado. #1256 (tensão AgentRun-vs-Wisk) está FECHADA desde 2026-09-07 pelo dono humano com decisão explícita (Wisk como runtime único do loop contínuo; knowledge/agent-runs/ mantido só como histórico legado) -- ver decision correspondente sobre por que esta rodada ainda produz um AgentRun apesar disso."
---

# Leitura: issues abertas

Levantamento via `mcp__github__list_issues` (state=OPEN, ordenado por
atualização) e leitura completa de `#1609`, `#1610`, `#1605` e `#1256` via
`issue_read`. Backlog de segurança (`docs/SECURITY_THREAT_MODEL.md`) é o
sinal mais forte de trabalho pronto e bem-especificado no repositório nesta
janela; issues de segmenter (#1050 e filhos) e de Parquet/CNJ (#1468-#1472,
#1022, #985) permanecem bloqueadas por falta de credenciais/permissão de
branch alheia neste tipo de sessão, fato já estabelecido por 10+ rodadas
anteriores (ver readings/checks de rodadas anteriores em
`knowledge/agent-runs/2026-09-25-exciting-mccarthy-r2xele/`).
