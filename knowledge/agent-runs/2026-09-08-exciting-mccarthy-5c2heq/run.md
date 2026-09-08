---
type: AgentRun
id: "2026-09-08-exciting-mccarthy-5c2heq"
started_at: "2026-09-08T22:00:58Z"
completed_at: ""
branch_at_start: "claude/exciting-mccarthy-5c2heq"
commit_at_start: "a82fe78449347edeb3d105827f3f0910112145c2"
claude_md_reading_id: "2026-09-08-exciting-mccarthy-5c2heq-reading-claude-md"
issues_reading_id: "2026-09-08-exciting-mccarthy-5c2heq-reading-issues"
prs_reading_id: "2026-09-08-exciting-mccarthy-5c2heq-reading-prs"
okf_reading_id: "2026-09-08-exciting-mccarthy-5c2heq-reading-okf"
goal_ids: []
primary_goal_id: ""
considered_work: []
selected_work: ""
expected_behavior: ""
entry_state: "new"
target_state: "red"
decision_ids: []
evidence_ids: []
check_ids: []
result_state: "red"
result_summary: ""
next_move: ""
---

# Agent run

Este arquivo é o scaffold deliberadamente incompleto da rodada. Copie-o para `knowledge/agent-runs/<run-id>/run.md` como primeira ação da sessão.

Em seguida rode:

```bash
uv run okf-parser check knowledge --relational-schema okf.schema.sql
```

Use as lacunas apontadas pelo contrato para conduzir a própria rodada.

Os componentes da sessão vivem no mesmo diretório e usam types próprios:

- `AgentReading`: confirma uma leitura real e registra o achado que ela trouxe;
- `AgentGoal`: declara objetivo, motivação e sinal observável de sucesso;
- `AgentDecision`: registra uma escolha relevante e sua razão;
- `AgentEvidence`: liga o avanço a evidência concreta, como teste, diff, CI, PR ou runtime;
- `AgentCheck`: registra uma verificação executada e pode apontar para a evidência correspondente.

As quatro leituras iniciais do `AgentRun` devem apontar para `AgentReading` sobre `CLAUDE.md`, issues abertas, PRs abertos e conhecimento OKF. Depois, crie goals tipados e preencha `goal_ids` e `primary_goal_id`. Decisões, evidências e checks surgem conforme o trabalho avança e seus IDs são acumulados neste relatório.

O relatório só amadurece porque o trabalho amadureceu. Rode o check novamente após cada avanço material e use o resultado para decidir o próximo passo.

**`completed_at` antes do primeiro push que abre PR.** `completed_at` vazio é aceitável apenas enquanto o relatório existe só localmente, durante a redação. `scripts/check_agent_run_completeness.py` roda em CI (job `validate` e via `tests/test_check_agent_run_completeness.py`) sobre toda `knowledge/agent-runs/`, inclusive relatórios de rodadas ainda em PR — então qualquer commit que leve este arquivo a um push (o que abre a PR) precisa já ter `completed_at` preenchido com um timestamp real, mesmo que `result_state` ainda seja `"review"` porque a PR está com CI pendente. Não confunda "rodada terminada" (quando a PR é mesclada) com "relatório completo" (exigido a partir do primeiro push): `completed_at` marca quando o trabalho ativo desta sessão concluiu, não quando a PR foi mesclada — se a PR precisar de mais um commit depois (correção de CI, revisão), atualize `result_state`/`result_summary`/`next_move` num commit seguinte sem apagar `completed_at`.

**Três testes falham enquanto o relatório está em rascunho, não só um.** Enquanto `completed_at`/`primary_goal_id`/`result_summary`/`next_move` deste `run.md` ainda estiverem vazios, rodar a suíte completa (`uv run pytest -q`) mostra até três falhas simultâneas, todas causadas pelo mesmo motivo (uma instância `AgentRun` incompleta no bundle `knowledge/`), não três problemas distintos: `tests/test_check_agent_run_completeness.py` (o próprio gate de completude), `tests/web/test_generate_okf_zod_schemas.py::test_generated_zod_schemas_file_matches_current_knowledge_bundle` e `tests/causaganha_mcp/test_okf_domain_models.py::test_generated_domain_models_file_matches_current_knowledge_bundle`. Os dois últimos falham porque `okf-parser` deriva a forma (opcional vs. obrigatório) dos schemas Zod/domain-model gerados a partir do conteúdo real de todas as instâncias do bundle — um `AgentRun` em rascunho com campos vazios muda temporariamente essa forma inferida em relação aos arquivos gerados já commitados. Não regenere `web/src/lib/processoConsultar.gen.ts` nem `src/causaganha_mcp/_generated/domain_models.py` para "corrigir" isso: os três testes voltam a passar sozinhos assim que este `run.md` for preenchido como qualquer outro relatório finalizado.
