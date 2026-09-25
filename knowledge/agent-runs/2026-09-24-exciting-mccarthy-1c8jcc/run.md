---
type: AgentRun
id: "2026-09-24-exciting-mccarthy-1c8jcc"
started_at: "2026-09-24T21:27:46Z"
completed_at: "2026-09-24T21:40:45Z"
branch_at_start: "claude/exciting-mccarthy-1c8jcc"
commit_at_start: "6e72fabfc16da9c0b42bde134576ceb9e580f6e2"
claude_md_reading_id: "2026-09-24-exciting-mccarthy-1c8jcc-reading-claude-md"
issues_reading_id: "2026-09-24-exciting-mccarthy-1c8jcc-reading-issues"
prs_reading_id: "2026-09-24-exciting-mccarthy-1c8jcc-reading-prs"
okf_reading_id: "2026-09-24-exciting-mccarthy-1c8jcc-reading-okf"
goal_ids:
  - "2026-09-24-exciting-mccarthy-1c8jcc-goal-eliminate-dispatch-injection"
primary_goal_id: "2026-09-24-exciting-mccarthy-1c8jcc-goal-eliminate-dispatch-injection"
considered_work:
  - "#1470/#1469/#1482/#1471/#1472/#1468/#1022/#985 (Parquet/CNJ): reconfirmadas bloqueadas por credenciais Internet Archive ausentes neste tipo de sessao, fato ja estabelecido por 8+ rodadas anteriores. Nao selecionadas."
  - "#1605 (batch27 de #1050, branch alheia claude/exciting-mccarthy-034xwb): mergeable_state=dirty (conflito real em data/segmenter/annotations/), ja diagnosticado por 2+ rodadas anteriores (e3tk18, p973xb) como fora do alcance desta sessao sem permissao explicita de push naquela branch. Reconfirmado, nao selecionado."
  - "#1619 (fecha #1615/TM-07, de sessao Wisk concorrente): mergeable_state=clean, 10/10 checks verdes, 0 review bloqueante. Mesclada imediatamente no inicio da rodada, antes de qualquer trabalho de dominio (ver decision-merge-1619-first)."
  - "#1353 (dependabot bump @vitest/mocker, deployment/relay-cf): parada ha 15 dias, fora de escopo, baixa prioridade. Nao selecionada."
  - "#1608 (security(ci): eliminar eval em workflow_dispatch com secrets, TM-01): proximo item na ordem de execucao explicita do threat model apos #1612/TM-09 (fechada pela rodada anterior) e #1615/TM-07 (fechada nesta rodada via #1619). Bem escopada, self-contained, gate automatizado definido no corpo da issue, nao depende de credenciais externas. Selecionada como trabalho principal desta rodada -- com escopo expandido para os 5 workflows adicionais que a auditoria pedida pela propria issue encontrou com o mesmo padrao (ver decision-fix-all-six-workflows)."
selected_work: "Mesclar #1619 (ja pronta, de sessao concorrente). Em seguida, TDD completo sobre #1608/TM-01: demonstrar ao vivo (antes de qualquer mudanca) que a interpolacao ${{ inputs.X }} dentro do corpo de um script run: e, por si so, uma injecao de codigo explorável em .github/workflows/tjro-sync.yml (job secret-bearing); auditar todos os workflows com workflow_dispatch.inputs e encontrar o mesmo padrao em datajud-enrich.yml (eval explicito), bootstrap-corpus.yml e collect-zips.yml (interpolacao direta sem eval, secrets IA), roundtrip-check.yml e sample-segmenter-texts.yml (interpolacao direta sem eval, sem secrets); escrever tests/test_workflow_dispatch_injection.py cobrindo os 6 workflows (assercao estatica sem eval/interpolacao + execucao real via bash com stub de 'uv' provando rejeicao de payloads maliciosos e argv exato para inputs validos); confirmar RED contra o conteudo original via git stash; corrigir os 6 arquivos .yml (mover inputs para env:, validar formato fechado, trocar eval/execucao nao-quotada por array Bash); confirmar GREEN; rodar ruff check/format --check e a suite completa de testes do repositorio; abrir PR referenciando #1608."
expected_behavior: "Ver success_signal em goal-eliminate-dispatch-injection."
entry_state: "new"
target_state: "green"
decision_ids:
  - "2026-09-24-exciting-mccarthy-1c8jcc-decision-merge-1619-first"
  - "2026-09-24-exciting-mccarthy-1c8jcc-decision-fix-all-six-workflows"
evidence_ids:
  - "2026-09-24-exciting-mccarthy-1c8jcc-evidence-red-workflow-injection-demo"
  - "2026-09-24-exciting-mccarthy-1c8jcc-evidence-red-pytest"
  - "2026-09-24-exciting-mccarthy-1c8jcc-evidence-green-pytest"
check_ids:
  - "2026-09-24-exciting-mccarthy-1c8jcc-check-workflow-injection-tests"
  - "2026-09-24-exciting-mccarthy-1c8jcc-check-ruff"
  - "2026-09-24-exciting-mccarthy-1c8jcc-check-okf-parser-final"
  - "2026-09-24-exciting-mccarthy-1c8jcc-check-agent-run-completeness-final"
result_state: "review"
result_summary: "Rodada com duas frentes. (1) Landing: mesclada #1619 ('security(datajud): validate tribunal against canonical allowlist (#1615)', de uma sessao Wisk concorrente que terminou minutos antes desta rodada), CI 10/10 verde e mergeable_state=clean confirmados antes do merge (sha 111dad0) -- fecha #1615/TM-07 (validacao de tribunal contra allowlist canonico nas tools MCP de DataJud). (2) Dominio: fechado #1608/TM-01 (injecao de comando via workflow_dispatch) com TDD completo e escopo expandido para 6 workflows, nao so o citado no titulo da issue. Uma demonstracao ao vivo, antes de qualquer mudanca de producao (evidence-red-workflow-injection-demo), extraiu o script real do step 'Crawl JURIS' de .github/workflows/tjro-sync.yml via yaml.safe_load, simulou a substituicao textual literal que o GitHub Actions faz para '${{ inputs.tjro_mes }}' com um payload malicioso, e executou o resultado via bash com um stub de 'uv' -- confirmando execucao arbitraria de comando (um 'touch' injetado rodou de fato) num job com IA_ACCESS_KEY/IA_SECRET_KEY/RELAY_TOKEN no ambiente, mesmo sem o 'eval' citado no titulo da issue rodar primeiro: a vulnerabilidade acontece na propria substituicao ${{ }} do GitHub Actions, antes do bash processar o script. Auditando todos os workflows com workflow_dispatch.inputs (pedido explicito da propria issue), encontrado o mesmo padrao em mais 5 arquivos alem de tjro-sync.yml: datajud-enrich.yml (eval explicito, mesmas credenciais IA), bootstrap-corpus.yml e collect-zips.yml (interpolacao direta sem eval, mesmas credenciais IA -- collect-zips.yml roda a cada 20 minutos), roundtrip-check.yml e sample-segmenter-texts.yml (interpolacao direta sem eval, sem secrets no job). Corrigidos os 6: todo input de workflow_dispatch passou a chegar via 'env:' (nunca mais interpolado como ${{ inputs.X }}/${{ github.event.inputs.X }} dentro do texto de um script run:), 'eval' removido dos 2 arquivos que o usavam, execucao nao-quotada de string ($CMD) trocada por array Bash ('CMD=(...)' + '\"${CMD[@]}\"') nos demais, e validacao de formato fechado adicionada para cada input (anos/inteiros via regex ^[0-9]+$/^[0-9]{4}$, datas via ^[0-9]{4}-[0-9]{2}-[0-9]{2}$, tjro_tipos contra o allowlist fechado de tjro_juris.client.TIPOS, tribunal/datajud via ^[a-z0-9]{2,10}$). Escrito tests/test_workflow_dispatch_injection.py (49 casos): assercoes estaticas (sem eval, sem interpolacao de dispatch input no corpo do run:) e execucao real via subprocess bash com stub de 'uv' provando que payloads com ';', '$()', crase e newline sao rejeitados (exit != 0, nenhuma chamada ao stub, nenhum marcador criado) e que inputs validos geram exatamente o argv esperado, incluindo o comportamento de default do cron (--desde-ano 1988) preservado. RED confirmado via 'git stash' dos 6 arquivos originais (30 dos 49 casos falharam, ver evidence-red-pytest) antes de qualquer mudanca de producao ser commitada; GREEN apos a correcao (evidence-green-pytest, 49 passed). uv run ruff check/format --check limpos (check-ruff). uv run pytest -q (suite completa do repositorio) rodou sem nenhuma regressao fora do proprio placeholder deste run.md -- a unica falha observada foi tests/test_check_agent_run_completeness.py::test_main_over_this_rounds_own_report_tree_is_complete, exatamente o comportamento documentado pelo proprio scaffold enquanto completed_at/primary_goal_id/result_summary/next_move deste relatorio ainda estao vazios; resolve sozinho assim que este commit finalizar o run.md (reconfirmar com check-agent-run-completeness-final apos preencher este campo). #1605 (batch27, branch alheia) permanece intocada por falta de permissao explicita de push -- mesmo diagnostico ja registrado por 2+ rodadas anteriores, sem fato novo que o revertesse."
next_move: "Uma rodada futura deve: (1) reconfirmar que a PR desta rodada (issue #1608) foi mesclada; (2) reconfirmar #1605 (batch27, branch claude/exciting-mccarthy-034xwb) -- permanecia mergeable_state=dirty no momento desta leitura; so uma sessao com permissao para editar aquela branch especifica (ou o dono humano) pode resolver o conflito; (3) com #1608/TM-01, #1612/TM-09 e #1615/TM-07 fechadas, o backlog de seguranca de docs/SECURITY_THREAT_MODEL.md tem 6 issues remanescentes na ordem de execucao da Sec5: #1609 (relay/DJEN proxy egress), #1610 (boundary unica de URLs de manifesto + identidade de geracao), #1611 (budgets de ingestao), #950 (rate limit do MCP publico), #1613 (CSP + piso XSS/runtime remoto), #1614 (lock/build/container/SBOM reproduziveis), #1616 (contrato machine-readable de conteudo nao confiavel para agentes) -- cada uma e candidata a uma rodada TDD self-contained como esta; a propria Sec5 do threat model sugere #1609 em seguida; (4) a validacao de 'tribunal' introduzida por #1619/#1615 cobre as tools MCP de DataJud (src/datajud/tribunais.py) mas nao o path da CLI 'datajud enrich --tribunal' usado por datajud-enrich.yml (agora com validacao de formato no proprio workflow, mas sem enforcement do allowlist canonico completo em src/datajud/service.py::enrich) -- um achado novo desta rodada, nao urgente (a validacao de formato do workflow ja fecha a superficie de injecao de shell), mas que uma rodada futura pode considerar unificar com validar_tribunal(); (5) a tensao AgentRun-vs-Wisk (issue #1256) permanece sem reconciliacao formal do dono humano e sem fato novo desde a ultima escalacao -- nao reescalar sem fato novo."
---

# Agent run

Rodada com duas frentes: (1) landing de trabalho ja pronto de uma
sessao Wisk concorrente (`#1619`, fecha `#1615`/TM-07 -- validacao de
`tribunal` contra allowlist canonico nas tools MCP de DataJud); (2)
fechamento de `#1608`/TM-01 (injecao de comando via
`workflow_dispatch`) com escopo expandido para os 6 workflows do
GitHub Actions que compartilham o mesmo padrao vulneravel, nao so o
citado no titulo da issue.

Uma demonstracao ao vivo (`evidence-red-workflow-injection-demo`)
provou, antes de qualquer mudanca de producao, que a vulnerabilidade
real e a interpolacao `${{ inputs.X }}` dentro do texto de um script
`run:` -- explorável mesmo sem o `eval` citado no titulo da issue, que
e um segundo estagio da mesma familia de bug.
