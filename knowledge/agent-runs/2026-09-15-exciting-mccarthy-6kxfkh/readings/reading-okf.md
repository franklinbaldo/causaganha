---
type: AgentReading
id: "2026-09-15-exciting-mccarthy-6kxfkh-reading-okf"
run_id: "2026-09-15-exciting-mccarthy-6kxfkh"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/index.md, .claude/hourly-loop.md, .wisk/knowledge/experiences/handoffs/*, wisk cadence.py source, knowledge/agent-runs/2026-09-15-exciting-mccarthy-pxa8pi/run.md (rodada anterior mais recente)"
finding: "Tensao AgentRun-vs-Wisk confirmada, inalterada em substancia desde a ultima reconfirmacao (pxa8pi, mesma tarde), mas com um fato novo e concreto apurado nesta rodada: 'wisk start'/'wisk session next' respondiam 'no-eligible-session'/null nao por cooldown ou cadencia, mas porque este checkout fresco (container novo) simplesmente nunca tinha rodado 'wisk init .' -- o bundle gerado e gitignored (SessionType/CadencePolicy/RunSpec sob .wisk/knowledge/system ou equivalente) nao existia. Rodei 'uv run wisk init .' (54 arquivos gerenciados criados, 1244 preservados) e 'wisk start' passou a resolver corretamente para o handoff #1471 (session-types/standard-experience, selection_reason=handoff-continuation) -- confirma que o loop Wisk em si nao esta quebrado, so precisa do init por checkout, exatamente como .claude/hourly-loop.md ja documentava. Isso e informacao nova e acionavel (nao apenas uma reconfirmacao), mas nao muda a decisao operacional desta rodada: o prompt agendado desta sessao especifica ('exciting-mccarthy') continua, sem ressalva, instruindo o scaffold AgentRun legado, e a tensao de fundo (dois mecanismos de loop coexistindo) ja foi escalada uma vez (to0ars, 2026-09-14) sem fato que justifique repetir a notificacao. O handoff Wisk ativo (#1471, publicacao real no IA) segue bloqueado por IA_ACCESS_KEY/IA_SECRET_KEY ausentes deste ambiente -- mesmo bloqueio ha 6 rodadas consecutivas, incluindo agora confirmado tambem sob o proprio Wisk inicializado."
---

# Leitura: conhecimento OKF relevante

Fui alem da reconfirmacao textual de rodadas anteriores: tracei a fonte de
`wisk/cadence.py` para entender por que `wisk start` reportava
`no-eligible-session`/`null`, e descobri que o bundle gerado (SessionType/
CadencePolicy) simplesmente nao existia neste checkout fresco -- `grep -rl
'type: "SessionType"' .wisk/` e `'type: "CadencePolicy"'` retornaram vazio.
Rodei `uv run wisk init .` (conforme `.claude/hourly-loop.md` ja instruia
para "checkout novo ou ainda nao inicializado") e `wisk start` passou a
funcionar, resolvendo para o handoff `#1471` (publicacao IA pendente,
bloqueado por credenciais ausentes -- mesmo bloqueio de 6 rodadas Wisk
anteriores). Isso descarta a hipotese de que o loop Wisk esteja quebrado
estruturalmente; e apenas init-per-checkout, como documentado.

Isso nao muda a decisao operacional: o prompt agendado desta sessao
("exciting-mccarthy") continua instruindo o scaffold AgentRun legado sem
ressalva, e a tensao de fundo ja foi escalada uma vez (to0ars, 14/09) sem
fato que justifique repetir a notificacao agora -- ver
decision-follow-scheduled-scaffold-with-verified-wisk-state. Trabalho de
dominio real escolhido: continuar a escala de ReviewRecords de #1051
(review_count=21 no inicio desta rodada, confirmado ao vivo).
