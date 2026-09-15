---
type: AgentRun
id: "2026-09-15-exciting-mccarthy-6d5vnd"
started_at: "2026-09-15T06:25:55Z"
completed_at: "2026-09-15T06:40:00Z"
branch_at_start: "claude/exciting-mccarthy-6d5vnd"
commit_at_start: "87cf5f008fd0003486562b261ca05eefd95127bc"
claude_md_reading_id: "2026-09-15-exciting-mccarthy-6d5vnd-reading-claude-md"
issues_reading_id: "2026-09-15-exciting-mccarthy-6d5vnd-reading-issues"
prs_reading_id: "2026-09-15-exciting-mccarthy-6d5vnd-reading-prs"
okf_reading_id: "2026-09-15-exciting-mccarthy-6d5vnd-reading-okf"
goal_ids:
  - "2026-09-15-exciting-mccarthy-6d5vnd-goal-bloom-filter-a1c"
primary_goal_id: "2026-09-15-exciting-mccarthy-6d5vnd-goal-bloom-filter-a1c"
considered_work:
  - "Reescalar a tensão AgentRun-vs-Wisk por notificação proativa: rejeitado -- evidência nova (round Wisk real mesclado, #1499/#1500) confirma a predição já escalada duas vezes, mas não introduz decisão nova; ver decision-follow-scheduled-scaffold-again."
  - "Continuar o epic #1468/#1471/#1472 publicando o candidato reordenado TJRO 2026 no Internet Archive: bloqueado de novo -- `env | grep -i 'IA_\\|ARCHIVE'` vazio, mesmo bloqueio confirmado por toda rodada (AgentRun e Wisk) desde pelo menos 11/09."
  - "Implementar a superfície pública de busca de decisões (#1093): o próprio dono marcou a issue como 'ESPECIFICADA, mas NÃO é prioridade imediata', gated por #950 (endpoint MCP remoto) -- fora de escopo para esta rodada."
selected_work: "Resolver o flag [speculative até medir em produção] do item A1c (gate do índice covering, §1c) em docs/planning/parquet-storage-optimization-plan.md, confirmando com dois arquivos Parquet reais de produção se o layout CNJ-first já decidido para comunicacoes precisa de um índice covering aditivo."
expected_behavior: "Ver success_signal em goal-bloom-filter-a1c."
entry_state: "new"
target_state: "review"
decision_ids:
  - "2026-09-15-exciting-mccarthy-6d5vnd-decision-follow-scheduled-scaffold-again"
  - "2026-09-15-exciting-mccarthy-6d5vnd-decision-covering-index-not-needed"
evidence_ids:
  - "2026-09-15-exciting-mccarthy-6d5vnd-evidence-red-test"
  - "2026-09-15-exciting-mccarthy-6d5vnd-evidence-green-test"
  - "2026-09-15-exciting-mccarthy-6d5vnd-evidence-production-benchmark-large-item"
  - "2026-09-15-exciting-mccarthy-6d5vnd-evidence-production-benchmark-borderline-item"
check_ids:
  - "2026-09-15-exciting-mccarthy-6d5vnd-check-okf-parser-after-readings-goal-decision"
  - "2026-09-15-exciting-mccarthy-6d5vnd-check-full-suite-mid-round"
  - "2026-09-15-exciting-mccarthy-6d5vnd-check-okf-parser-final"
result_state: "review"
result_summary: "Epic #1468/#1469 (Parquet nativo por CNJ) teve quase todos os critérios de aceite fechados por rodadas anteriores (AgentRun e, nesta janela pela primeira vez com evidência observável, também Wisk -- PR #1499/#1500 mesclada em main fechando os critérios não-gated-por-IA de #1470). O único item de arquitetura do plano de storage ainda aberto e desbloqueado era A1c: o gate da decisão do índice covering aditivo (§1c), que o plano proibia decidir a partir só do benchmark sintético bloom_cardinality.py. Esta rodada baixou os dois arquivos Parquet reais já usados por A1b (djen-tjro-2026, 1.041.723 linhas; djen-2025-12-23, 95.783 linhas), escreveu um novo script (scripts/benchmarks/bloom_filter_production.py) que reescreve cada um sob os dois layouts candidatos (numero_processo-first, o real de exporter.py, e data-first) com WRITE_BLOOM_FILTER true e ROW_GROUP_SIZE 122880, e inspecionou parquet_metadata() por bloom_filter_offset/encoding por row group da coluna numero_processo, além do pruning min/max para o mesmo point-lookup. Resultado real, nos dois arquivos: NENHUMA ordenação ganha bloom filter (100% PLAIN) -- a repetição real por CNJ é baixa demais para dictionary-encoding num row group de ~115K linhas, confirmando o caso 'CNJ quase único' que a matriz sintética já sinalizava como possível, mas nunca confirmado em produção. Apesar disso, a ordenação numero_processo-first (já em produção) continua podando o point-lookup a 1 row group via min/max sozinho -- o mesmo resultado ideal que A1b já havia medido -- enquanto data-first toca todos os row groups do item grande. Decisão registrada (decision-covering-index-not-needed): o índice covering aditivo NÃO é necessário. TDD: um teste em tests/test_bloom_filter_production.py::TestDecideCoveringIndex sobre a função pura decide_covering_index (RED via renomeação temporária -> ImportError na coleta; GREEN com a implementação restaurada, 3/3 testes). docs/planning/parquet-storage-optimization-plan.md atualizado em 2 pontos (bloco de confirmação real logo após a matriz sintética do §1c; linha A1c da tabela de rastreamento) removendo o flag [speculative] e citando as duas evidências JSON reais (docs/planning/evidence/bloom-filter-a1c-production*.json) -- deixei explícito que a medição usa parquet_metadata (mesmo método de A1b), não byte-count httpfs real, porque o arquivo publicado no IA ainda não tem o layout novo (bloqueado por #1472/credenciais). uv run pytest -q mostrou apenas a cascata esperada de 1 falha (test_check_agent_run_completeness, causada pelo próprio run.md em rascunho) antes de preencher este cabeçalho -- ruff check/format limpos em todo o repositório."
next_move: "Após esta PR mesclar, comentar em #1469 marcando o critério de A1c/índice covering como fechado (mesmo padrão das rodadas anteriores) e revisar se o checklist do próprio #1468 já pode ser marcado como completo -- com A1b, A1c, a unificação exporter.py/consolidate.py, a certificação de rodapé, a leitura direta em processoCnj.ts e a ordem física em reconcile_processos.py todos fechados, o item 1 do checklist de #1468 ('Implementação compatível incorporada e validada') parece inteiramente resolvido em código; só resta a publicação real no IA (#1472), bloqueada por IA_ACCESS_KEY/IA_SECRET_KEY (inalterado desde 11/09 -- precisa de sessão com credenciais de escrita reais, seja AgentRun ou Wisk, o handoff Wisk ativo handoff-issue-1471-ia-publish-pending já documenta o mesmo bloqueio). Domínio para rodada futura sem depender de credenciais: revisar a fila de issues fora do cluster Parquet/CNJ (#1093 web/teor -- explicitamente não-prioritária pelo dono, gated por #950; cluster segmenter #1047-1057/#884/#886/#887 -- gated por infra de GPU/anotação; #1022/#985 datasets TCU/TSE). A tensão AgentRun-vs-Wisk permanece sem reconciliação humana, mas nesta rodada ganhou evidência observável concreta (PR Wisk real mesclada na mesma janela, não só a declaração de política em .claude/hourly-loop.md) -- uma futura rodada deve verificar se o mantenedor já agiu (mudança no schedule ou no hourly-loop.md) antes de decidir se uma nova notificação é justificada; nenhuma foi enviada nesta rodada por não haver decisão nova pendente do usuário."
---

# Agent run

Rodada de continuidade sobre o epic #1468/#1469 (Parquet nativo por CNJ). Nesta janela não há PR de domínio em voo (única PR aberta é a dependabot #1353, stale) nem handoff Wisk que compita com o trabalho escolhido -- o round Wisk mais recente (20260915T052720Z, PR #1499/#1500) já fechou os critérios não-gated-por-IA de #1470. A lacuna real e desbloqueada que restava no plano de storage era A1c: o gate da decisão do índice covering aditivo (§1c) seguia `[speculative até medir em produção]`, com o próprio plano avisando explicitamente que a conclusão do benchmark sintético (`bloom_cardinality.py`) precisava ser confirmada em dados reais antes de prescrever ou descartar o índice. Esta rodada reescreveu os dois arquivos reais já usados por A1b sob os layouts candidatos e inspecionou `bloom_filter_offset`/encoding por row group, fechando a lacuna com evidência real: o índice covering não é necessário porque a ordenação já em produção poda o point-lookup a 1 row group via min/max, com ou sem bloom filter.
