---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-orr2e3-reading-issues"
run_id: "2026-09-25-exciting-mccarthy-orr2e3"
subject: "open_issues"
reference: "GitHub issues abertas, franklinbaldo/causaganha (list_issues, state=OPEN, 20 abertas)"
finding: "20 issues abertas: nenhuma de segurança (todas TM-* do threat model agora fecham em issues já CLOSED -- #1608/#1609/#1610/#1611/#1612/#1613/#1614/#1615/#1616/#1652 -- confirmado por releitura de `docs/SECURITY_THREAT_MODEL.md` e checagem individual). O restante é: Parquet/CNJ (#1470/#1469/#1471/#1472/#1468/#1022/#985), bloqueadas por credenciais IA ausentes neste tipo de sessão (10+ rodadas anteriores, sem fato novo); segmenter (#1050 e derivadas #1051/#1057/#1056/#1055/#1054/#1047/#1053/#884/#887/#886), trilha de anotação/experimento de longo prazo; #951 (entrada pública MCP) e #1093 (busca direta de teor), ambas com o mesmo bloqueio explícito no próprio corpo: dependem do rollout remoto do MCP (#950) primeiro. #950 aparecia como FECHADA na lista de issues (não está mais entre as 20 abertas) -- investigação profunda (ver reading-prs.md e decision-950-reopen) mostrou que essa é a descoberta central desta rodada: #950 foi fechada (10:15:17Z, PR #1630) citando a conclusão de #1629 ('closes #950/TM-06'), mas #1629 só fechou o sub-item TM-06 (rate limiting) do threat model, não os critérios de aceite do corpo de #950 (URL pública estável, smoke remoto, `mcp-rollout-proof.json`). `mcp__github__actions_list list_workflow_runs` para `deploy-mcp.yml` retornou `total_count: 0` -- o workflow de rollout nunca rodou nenhuma vez. Ou seja, #950 e #951 (que dependem dele) continuam de fato bloqueadas exatamente como as rodadas de 2026-09-01 a 2026-09-07 diagnosticaram (falta de autoridade/credencial de deploy Cloud Run nesta sessão), mas o rastreador (GitHub) e portanto qualquer rodada futura que confiar nele sem verificar ao vivo passaria a acreditar erroneamente que o MCP remoto já está publicado. Selecionado como o achado mais valioso desta rodada."
---

# Leitura: issues abertas

20 issues abertas revisadas via `list_issues` (state=OPEN). Todo o
backlog de segurança do threat model está fechado. O achado relevante
não veio de uma issue aberta, mas de uma fechada incorretamente: `#950`
(rollout MCP remoto) foi encerrada citando apenas a conclusão do
sub-item TM-06 (rate limiting), sem que o critério de aceite real do seu
próprio corpo (URL pública + prova de smoke) tivesse sido cumprido —
confirmado que `deploy-mcp.yml` nunca rodou (`0` workflow runs). Como
`#951`/`#1093` dependem explicitamente desse rollout, a issue-tracker
agora afirma uma coisa que o estado observável do repositório contradiz.
