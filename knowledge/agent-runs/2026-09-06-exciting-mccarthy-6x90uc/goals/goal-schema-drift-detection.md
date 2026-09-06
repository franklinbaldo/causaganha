---
type: AgentGoal
id: "2026-09-06-exciting-mccarthy-6x90uc-goal-schema-drift-detection"
run_id: "2026-09-06-exciting-mccarthy-6x90uc"
goal: "scripts/check_agent_run_completeness.py detecta, para qualquer documento Agent*-family, uma chave de frontmatter que não é uma coluna declarada em knowledge/okf.schema.sql para aquele tipo — sem falso positivo em nenhum dos 19 relatórios já existentes."
rationale: "yigsua (a rodada concluída imediatamente anterior) descobriu que `okf-parser check` só valida PK/FK de catálogo e que o próprio checker de completude deste projeto só verifica presença de campos exigidos, nunca se as chaves presentes são as certas — uma rodada pode nomear campos errados (title/motivation em vez de goal/rationale) e só descobrir isso muito depois, via diff inesperado em `pytest -q` nos arquivos gerados. Sem essa issue estar rastreada em nenhum dos 17 issues abertos (todos bloqueados por trabalho de GPU/anotação, upload credenciado ao vivo, decisão de deploy ao vivo, ou explicitamente despriorizados pelo dono), esta é a melhor oportunidade real de avanço desta rodada — reforçar a própria ferramenta que toda rodada futura do loop depende para não repetir o mesmo erro silencioso."
success_signal: "Uma nova função unknown_fields_for_type() existe e é usada por main(); testes RED (ImportError ao coletar) confirmados antes da implementação e GREEN (43/43 no módulo, 1472/1472 na suíte completa) depois; `uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs` continua retornando 0 sobre a árvore real (sem falso positivo); `uv run okf-parser check` permanece conformant; ruff check/format limpos; uma PR contendo só essa mudança de tooling + o relatório OKF desta rodada é aberta e mesclada."
status: "achieved"
---

# Goal: detectar schema drift em campos Agent*-family

Fechar a lacuna que a rodada `yigsua` descobriu: nomes de campo divergentes do schema não são detectados no momento do `okf-parser check`, só depois via diff inesperado em `pytest`.
