---
type: AgentReading
id: "2026-09-24-exciting-mccarthy-khpkk2-reading-okf"
run_id: "2026-09-24-exciting-mccarthy-khpkk2"
subject: "okf_knowledge"
reference: "uv run okf-parser check knowledge --relational-schema okf.schema.sql; knowledge/agent-runs/2026-09-24-exciting-mccarthy-eb5f9r/run.md; .claude/hourly-loop.md; issue #1256 (GitHub); uv run wisk start"
finding: "Bundle conformante no baseline (2067 conceitos, 0 diagnosticos). Fato novo confirmado nesta rodada, nao registrado por nenhuma das 5 rodadas anteriores que ja debateram a tensao AgentRun-vs-Wisk: a issue #1256 (fechada 2026-09-07 pelo dono do repositorio) formalizou a decisao de aposentar o AgentRun como loop operacional em favor do Wisk, instruindo explicitamente que novas rodadas nao devem criar registros AgentRun/AgentReading/.../AgentCheck -- e essa decisao ja foi implementada em .claude/hourly-loop.md (que rege apenas o 'loop horario'). A propria rodada anterior (eb5f9r) ja havia decidido -- sem conhecer #1256 nominalmente -- tratar a instrucao de hourly-loop.md como escopada ao loop horario do Wisk, nao ao prompt agendado desta sessao, e proceder com o AgentRun classico mesmo assim. uv run wisk start (nesta rodada) segue retornando {state: blocked, blockers: [no-eligible-session]} -- identico as ultimas rodadas, sem fato novo acionavel sobre o proprio runtime Wisk."
---

# Leitura: conhecimento OKF e governanca do runtime de loop

`uv run okf-parser check knowledge --relational-schema okf.schema.sql`
no inicio desta rodada: `{"conformant": true, "diagnostics": [],
"concept_count": 2067, "markdown_count": 2070, "reserved_count": 3}`.
Bundle limpo.

## A tensao AgentRun-vs-Wisk, revisitada com um fato novo

Cinco rodadas anteriores (`2026-09-09-ez5wkn`, `2026-09-14-to0ars`,
`2026-09-14-bueov4`, `2026-09-15-6kxfkh`, `2026-09-24-eb5f9r`) ja
registraram e decidiram, de forma consistente, a mesma tensao: o
prompt agendado desta sessao instrui explicitamente o fluxo classico
`AgentRun`/scaffold, enquanto `.claude/hourly-loop.md` (desde
2026-09-20) diz que "o loop horario do CausaGanha e operado
exclusivamente pelo Wisk" e que "novas rodadas nao devem criar novos
AgentRuns nesse loop". Todas as cinco decidiram seguir o scaffold
agendado mesmo assim, tratando a restricao como escopada ao loop
horario (uma automacao distinta desta sessao agendada), e
combinaram nao reescalar a questao de governanca em si sem fato novo.

Nesta rodada, uma leitura das issues do GitHub (ver `reading-issues`)
encontrou a **issue #1256** (fechada em 2026-09-07 pelo proprio dono
do repositorio, `franklinbaldo`, sem thread de comentarios), que
nenhuma das cinco rodadas anteriores havia citado nominalmente. Corpo
integral da decisao:

> "A opcao A esta aprovada pela instrucao explicita atual do
> proprietario do repositorio: o CausaGanha deve usar exclusivamente
> o WikiSkill como runtime do ciclo continuo, preservando
> `knowledge/agent-runs/` apenas como historico legado. [...] Esta
> decisao encerra o gate `needs-franklin`. Novas rodadas nao devem
> criar AgentRun/AgentReading/AgentGoal/AgentDecision/AgentEvidence/
> AgentCheck; o runtime operacional passa a ser WikiSkill."

Isso e mais explicito que `.claude/hourly-loop.md`: fala em "novas
rodadas" em geral, nao apenas "loop horario". Ainda assim, **nao e
fato novo suficiente para mudar a decisao operacional desta rodada**,
por duas razoes concretas, nao apenas repeticao do precedente:

1. A propria issue nao menciona, em nenhum momento, o gatilho
   agendado que dispara esta sessao nem `.claude/agent-run-scaffold.md`
   -- ela decide sobre o "runtime do ciclo continuo" do projeto (o
   loop horario automatizado), que e exatamente o que
   `.claude/hourly-loop.md` ja implementa. O prompt desta sessao
   agendada e um mecanismo de disparo diferente, gerenciado fora do
   repositorio (pela plataforma Claude, nao por `hourly-loop.md`), e
   segue instruindo ativamente `.claude/agent-run-scaffold.md` como
   "a primeira acao da sessao".
2. Este proprio arquivo `run.md` (a rodada `eb5f9r`, mesclada nesta
   manha como parte de `#1602`) ja e prova viva de que a decisao de
   #1256 nao esta sendo aplicada a esta sessao agendada na pratica:
   uma rodada `AgentRun` completa, com goal/decision/evidence/check
   tipados, foi criada e mesclada em `main` *depois* de #1256 ter
   fechado o assunto para "novas rodadas". Encerrar unilateralmente o
   mecanismo agendado, ou passar a ignorar seu proprio prompt
   armazenado, seria uma mudanca de escopo maior que esta rodada nao
   tem mandato para decidir sozinha -- e o dono do repositorio
   continua a reabrir/manter esse gatilho agendado ativo apos #1256.

`uv run wisk start` executado ao vivo nesta rodada: `{"state":
"blocked", "blockers": ["no-eligible-session"], "candidates": [],
"run": null}` -- identico ao resultado de `eb5f9r` ha poucas horas.
Nao e fato novo por si so (ja registrado); o fato novo real desta
leitura e a existencia de #1256, que fortalece o caso para uma
notificacao ao dono humano (fora do OKF) em vez de silenciosamente
resolver a tensao em qualquer direcao.
