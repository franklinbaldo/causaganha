---
type: AgentReading
id: "2026-09-26-exciting-mccarthy-ku8qje-reading-claude-md"
run_id: "2026-09-26-exciting-mccarthy-ku8qje"
subject: "claude_md"
reference: "CLAUDE.md"
finding: "Releitura integral no início da rodada. Nenhum trabalho planejado desta rodada toca djen-backup/manifest, contratos `.qmd` ou a fronteira Panda/Svelte, então a maior parte do guia não se aplica diretamente ao trabalho escolhido (crescimento do corpus do segmenter, issue #1050). O que se aplica de fato: a seção 'Before committing' (`uv run ruff check`, `ruff format --check`, `pytest -q`) foi seguida antes de qualquer commit desta rodada; e a disciplina geral de 'Correctness' (nunca aceitar um estado registrado como verdadeiro sem verificação ao vivo) motivou verificar `scripts/segmenter_governance_status.py` ao vivo (antes de assumir que mais adjudicação de #1051 ainda ajudaria) em vez de confiar no relato do handoff da rodada anterior sem reexecutar o script. Achado adicional (fora do CLAUDE.md, mas relevante para o processo da rodada): `.claude/hourly-loop.md` documenta que o mecanismo legado `AgentRun`/`knowledge/agent-runs/` foi descontinuado para o loop horário baseado em Wisk (`.wisk/knowledge/experiences/`), mas o prompt desta sessão especificamente instrui o uso do scaffold `AgentRun` legado -- tratado como uma segunda automação paralela e distinta do loop horário Wisk, não uma contradição a resolver: ambas convivem no mesmo repositório (confirmado por PR #1665, que chegou via o loop Wisk e foi mesclado por esta própria rodada)."
---

# Leitura: CLAUDE.md

Releitura integral no início da rodada. Pouco do guia se aplica
diretamente ao trabalho escolhido (crescimento de corpus do segmenter),
mas a disciplina de "Correctness" (verificar ao vivo antes de confiar em
um estado registrado) motivou reexecutar
`scripts/segmenter_governance_status.py` como primeiro passo antes de
aceitar a conclusão do handoff da rodada anterior. Achado de processo:
`.claude/hourly-loop.md` descontinuou o mecanismo `AgentRun` para o loop
horário Wisk, mas esta sessão é uma automação paralela e distinta que
usa deliberadamente o scaffold `AgentRun` legado -- ambas convivem no
mesmo repositório sem conflito real.
