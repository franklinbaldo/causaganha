---
type: AgentReading
id: "2026-09-25-exciting-mccarthy-e0vvbh-reading-okf"
run_id: "2026-09-25-exciting-mccarthy-e0vvbh"
subject: "okf_knowledge"
reference: "knowledge/agent-runs/index.md; .claude/hourly-loop.md; okf.schema.sql; rodadas de 2026-09-25 (3zkmxg, 95dnzq, r2xele, 9t0p2a)"
finding: "knowledge/agent-runs/index.md declara este mecanismo LEGADO ('não crie novos AgentRuns aqui') desde a migração para o runtime Wisk, e .claude/hourly-loop.md confirma: o loop horário normal usa exclusivamente 'uv run wisk start', com AgentRun/AgentReading/AgentGoal/AgentDecision/AgentEvidence/AgentCheck preservados só para auditoria histórica. A decisão está formalizada na issue #1256 (fechada em 2026-09-07 pelo dono humano, Opção A: Wisk como runtime único). Isso contradiz literalmente a primeira instrução do prompt desta sessão agendada ('a primeira ação da sessão é criar o relatório OKF... a partir de .claude/agent-run-scaffold.md'). As quatro rodadas anteriores de HOJE (3zkmxg, 95dnzq, r2xele, 9t0p2a) já identificaram exatamente essa tensão e decidiram, de forma consistente, continuar produzindo o AgentRun mesmo assim -- porque a decisão do dono humano resolveu a arquitetura do *repositório* (Wisk é o runtime do loop horário), mas não atualizou o *prompt da tarefa agendada externa* que efetivamente disparou esta sessão (algo fora do escopo de uma PR neste repositório). Nenhuma das quatro rodadas re-escalou por falta de fato novo suficiente. Esta rodada mantém a mesma leitura e o mesmo comportamento -- ver decision correspondente -- registrando que o próximo avanço real sobre essa tensão exige o dono humano atualizar a configuração do agendamento externo, não mais uma PR neste repositório."
---

# Leitura: conhecimento OKF

Releitura de `knowledge/agent-runs/index.md`, `.claude/hourly-loop.md` e do
histórico de rodadas de hoje (`2026-09-25-exciting-mccarthy-{3zkmxg,95dnzq,
r2xele,9t0p2a}/run.md`), além de `okf.schema.sql` para os contratos de tipo
usados neste relatório. A tensão AgentRun-vs-Wisk é conhecida, já
formalmente decidida no lado do repositório (#1256) e deliberadamente não
reescalada por múltiplas rodadas consecutivas sem fato novo -- este relatório
segue a mesma linha.
