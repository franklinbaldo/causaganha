---
type: AgentRun
id: "2026-09-25-exciting-mccarthy-9t0p2a"
started_at: "2026-09-25T04:30:00Z"
completed_at: "2026-09-25T06:41:00Z"
branch_at_start: "claude/exciting-mccarthy-9t0p2a"
commit_at_start: "7da38689f8a1db1c4c07461848116cd62eee27f3"
claude_md_reading_id: "2026-09-25-exciting-mccarthy-9t0p2a-reading-claude-md"
issues_reading_id: "2026-09-25-exciting-mccarthy-9t0p2a-reading-issues"
prs_reading_id: "2026-09-25-exciting-mccarthy-9t0p2a-reading-prs"
okf_reading_id: "2026-09-25-exciting-mccarthy-9t0p2a-reading-okf"
goal_ids:
  - "2026-09-25-exciting-mccarthy-9t0p2a-goal-mcp-untrusted-evidence-marker"
primary_goal_id: "2026-09-25-exciting-mccarthy-9t0p2a-goal-mcp-untrusted-evidence-marker"
considered_work:
  - "#1470/#1469/#1482/#1471/#1472/#1468/#1022/#985 (Parquet/CNJ): reconfirmadas bloqueadas por credenciais Internet Archive ausentes neste tipo de sessao, fato ja estabelecido por 10+ rodadas anteriores. Nao selecionadas."
  - "#1605 (batch27 de #1050, branch alheia claude/exciting-mccarthy-034xwb): sem PR verde acionavel por esta sessao (sem permissao de push naquela branch), mesmo diagnostico de rodadas anteriores. Nao selecionada."
  - "#1353 (dependabot bump @vitest/mocker, deployment/relay-cf): parada ha 16+ dias, fora de escopo, baixa prioridade. Nao selecionada."
  - "#1609/#1610: git log mostra que ambas ja receberam fatias adicionais (commits 2ce92d9, 7da3868) de sessoes concorrentes desde a ultima rodada registrada (r2xele); investigacao de codigo confirmou que o nucleo do invariante de #1610 (URL de manifesto validada antes de compor outro read_parquet) ja esta coberto nos pontos relevantes do repositorio. Nao selecionadas como trabalho principal nesta rodada."
  - "#1613 (CSP + piso XSS): tratavel em TDD, mas exige inventariar todos os sinks {@html} e desenhar uma CSP compativel com GitHub Pages/DuckDB-WASM -- escopo maior que #1616 para uma unica rodada. Preterida."
  - "#1614 (supply chain: lock/build/container/SBOM): decisoes de infraestrutura de build/deploy (digest de imagem, scanner de CI) fora do controle desta sessao, mesmo padrao que ja levou rodadas anteriores a preterir #1609. Nao selecionada."
  - "#1616 (security/mcp: marcar texto judicial como evidencia nao-confiavel): Python puro, um unico modulo (src/causaganha_mcp/tools/), sem credenciais externas, sem infraestrutura de deploy, gate automatizado explicito no corpo da issue, nenhuma rodada anterior registrada a tentou. Selecionada como trabalho principal."
selected_work: "TDD completo sobre o nucleo de #1616: escrever testes novos em tests/causaganha_mcp/test_untrusted_evidence_marker.py que RED-confirmam a ausencia de qualquer campo estrutural de confianca de conteudo em PublicacaoResult (publicacoes.py) e DecisaoResult (decisoes.py), incluindo um caso com trecho contendo uma frase de prompt injection; implementar um marcador Literal constante compartilhado (causaganha_mcp.evidence.UNTRUSTED_LEGAL_TEXT='untrusted_legal_text') exposto como campo tipo_conteudo nos dois modelos, preservando o texto original verbatim; atualizar as docstrings das duas tools e docs/MCP_AGENT_EXPERIENCE.md (secao Contrato de saida) e a linha TM-11 de docs/SECURITY_THREAT_MODEL.md para documentar a fronteira host/agente; confirmar GREEN; rodar ruff, a suite completa de tests/causaganha_mcp/ e a suite completa do repositorio antes de abrir a PR."
expected_behavior: "Ver success_signal em goal-mcp-untrusted-evidence-marker."
entry_state: "new"
target_state: "red"
decision_ids:
  - "2026-09-25-exciting-mccarthy-9t0p2a-decision-marker-scope-and-shape"
evidence_ids:
  - "2026-09-25-exciting-mccarthy-9t0p2a-evidence-red-untrusted-evidence-marker"
  - "2026-09-25-exciting-mccarthy-9t0p2a-evidence-green-untrusted-evidence-marker"
check_ids:
  - "2026-09-25-exciting-mccarthy-9t0p2a-check-ruff"
  - "2026-09-25-exciting-mccarthy-9t0p2a-check-mcp-suite"
  - "2026-09-25-exciting-mccarthy-9t0p2a-check-pytest-full-suite"
result_state: "review"
result_summary: "Fechado o nucleo da issue #1616 (TM-11 do threat model operacional, security(mcp)) com TDD completo. publicacoes_buscar e decisoes_buscar retornavam trecho (texto livre extraido de publicacoes/decisoes judiciais que um terceiro controla parcialmente) sem nenhum marcador estrutural distinguindo esse conteudo de uma instrucao para o agente que consome o MCP -- um host downstream com outras tools sensiveis poderia, por erro de composicao, tratar uma frase desse texto como comando. RED: tests/causaganha_mcp/test_untrusted_evidence_marker.py escrito primeiro contra a API alvo (causaganha_mcp.evidence.UNTRUSTED_LEGAL_TEXT, campo tipo_conteudo em PublicacaoResult/DecisaoResult) que ainda nao existia -- a propria colecao do modulo de teste falhou com ModuleNotFoundError, confirmando ausencia total da funcionalidade antes da mudanca. GREEN apos implementar: src/causaganha_mcp/evidence.py com a constante Literal compartilhada UNTRUSTED_LEGAL_TEXT; campo tipo_conteudo (mesmo Literal, com default e docstring) adicionado a PublicacaoResult (publicacoes.py) e DecisaoResult (decisoes.py) -- colocado no modelo de cada item, nao no envelope do resultado, entao nao tocou o contrato de campos de nivel superior ja fixado em tests/causaganha_mcp/test_tool_schema.py::_EXPECTED_OUTPUT_FIELDS. O marcador nunca sanitiza ou reescreve o texto -- trecho chega verbatim ao chamador mesmo quando contem uma frase like 'ignore todas as instrucoes anteriores'; ele so rotula, e o rotulo esta declarado no proprio JSON schema publicado de cada tool (const em $defs.PublicacaoResult/$defs.DecisaoResult), nao como metadado invisivel. Docstrings de publicacoes_buscar e decisoes_buscar, uma nova secao em docs/MCP_AGENT_EXPERIENCE.md ('Evidencia nao e instrucao (#1616)') e a linha TM-11 de docs/SECURITY_THREAT_MODEL.md foram atualizadas para documentar a fronteira host/agente e o escopo real da cobertura. tests/causaganha_mcp/test_untrusted_evidence_marker.py: 5/5 verde. uv run pytest -q tests/causaganha_mcp/ (36 arquivos): 100% verde. uv run ruff check/format --check: limpos no repositorio inteiro. uv run pytest -q (suite completa do repositorio): exit code 1 com exatamente 1 falha -- tests/test_check_agent_run_completeness.py::test_main_over_this_rounds_own_report_tree_is_complete -- a falha esperada e ja documentada em CLAUDE.md/scaffold enquanto este proprio run.md permanece em rascunho (completed_at/result_summary/next_move vazios no momento em que a suite rodou); nenhuma outra falha em nenhum outro modulo do repositorio, confirmando ausencia de regressao. Fora de escopo explicito desta rodada, registrado como follow-up: os campos de texto livre de processo_consultar (DocumentoResult.resumo, StjAcordaoResult.tese/ementa em src/causaganha_mcp/tools/processo.py) sao gerados por scripts/generate_okf_domain_models.py a partir de um TypeContract OKF em knowledge/, entao estender o marcador la exige uma mudanca de TypeContract + regeneracao dos arquivos com drift-check (tests/causaganha_mcp/test_okf_domain_models.py, tests/web/test_generate_okf_zod_schemas.py), maior que o que cabe com seguranca junto do resto do trabalho desta rodada. Achado relevante desta rodada, nao acionado por falta de fato novo: knowledge/agent-runs/index.md e .claude/hourly-loop.md documentam que o mecanismo AgentRun e legado, substituido pelo runtime Wisk para o loop horario -- mas o prompt desta sessao agendada instruiu explicitamente o uso do scaffold AgentRun, e multiplas rodadas registradas no mesmo dia (r2xele, 95dnzq, 3zkmxg e outras) continuam usando o mesmo mecanismo sem nenhuma reconciliacao. Essa tensao ja e a issue #1256, ja escalada por rodadas anteriores; sem fato novo desde a ultima escalacao, nao reescalada aqui, apenas reconfirmada."
next_move: "Uma rodada futura deve: (1) reconfirmar que a PR desta rodada (issue #1616, nucleo em publicacoes_buscar/decisoes_buscar) foi mesclada; (2) considerar estender o mesmo marcador tipo_conteudo=untrusted_legal_text aos campos de texto livre de processo_consultar (DocumentoResult.resumo, StjAcordaoResult.tese/ementa) -- isso exige uma mudanca de TypeContract OKF em knowledge/ (nao apenas um campo Pydantic novo) seguida de uv run python scripts/generate_okf_domain_models.py e da atualizacao correspondente em web/src/lib/processoConsultar.gen.ts, com os testes de drift (test_okf_domain_models.py, test_generate_okf_zod_schemas.py) como gate; (3) apos #1616, o backlog de seguranca de docs/SECURITY_THREAT_MODEL.md tem 2 issues remanescentes sem PR em voo: #1613 (CSP + piso XSS, exige inventario de sinks {@html} + CSP compativel com GitHub Pages/DuckDB-WASM) e #1614 (supply chain: uv.lock frozen, digest de imagem, usuario nao-root no MCP Docker, SBOM, scanner de CI -- decisoes de infraestrutura de build/deploy, historicamente preteridas por sessoes deste tipo); dentre as duas, #1613 parece mais tratavel em uma unica rodada de TDD self-contained (web/TypeScript) do que #1614 (infra de build/deploy); (4) #1605 (batch27 do segmenter, branch alheia claude/exciting-mccarthy-034xwb) permanece com o mesmo diagnostico de bloqueio por falta de permissao de push ha 4+ rodadas -- so uma sessao com permissao para editar aquela branch especifica (ou o dono humano) pode resolve-lo; (5) a tensao AgentRun-vs-Wisk (issue #1256, knowledge/agent-runs/index.md vs. .claude/hourly-loop.md vs. o prompt desta sessao agendada) permanece sem reconciliacao formal do dono humano -- reconfirmada nesta rodada sem fato novo suficiente para reescalar, mas o dono humano pode querer atualizar o prompt da sessao agendada ou a documentacao para eliminar a divergencia."
---

# Agent run

Rodada de continuidade na janela de seguranca operacional aberta por
`docs/SECURITY_THREAT_MODEL.md`. Nenhuma PR de continuidade estava pronta
para merge (diferente das ultimas 3 rodadas da mesma janela); o trabalho
comecou do zero sobre `#1616` (TM-11: marcar texto judicial retornado
pelo MCP como evidencia nao-confiavel, nunca instrucao). TDD completo
(RED -> GREEN), documentacao atualizada (`docs/MCP_AGENT_EXPERIENCE.md`,
`docs/SECURITY_THREAT_MODEL.md`), suite completa do repositorio verde
exceto a falha esperada e auto-resolvivel deste proprio relatorio em
rascunho. Ver `goal_ids`/`decision_ids`/`evidence_ids`/`check_ids` para o
processo completo.
