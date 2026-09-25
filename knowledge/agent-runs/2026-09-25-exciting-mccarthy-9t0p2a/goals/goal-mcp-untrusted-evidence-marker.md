---
type: AgentGoal
id: "2026-09-25-exciting-mccarthy-9t0p2a-goal-mcp-untrusted-evidence-marker"
run_id: "2026-09-25-exciting-mccarthy-9t0p2a"
goal: "Fechar o nucleo de #1616 (security/mcp): dar a `publicacoes_buscar` e `decisoes_buscar` um marcador estrutural, estavel e machine-readable de que todo texto judicial retornado (em especial `trecho`) e evidencia preservada, nunca instrucao executavel para um agente."
rationale: "As duas tools retornam `trecho`, texto livre extraido de publicacoes/decisoes judiciais que um autor mal-intencionado controla parcialmente. Um host downstream com outras tools sensiveis pode, por erro de composicao, tratar uma frase desse texto como comando. O MCP nao pode impor a politica de tools do agente consumidor, mas pode tornar a fronteira semantica inequivoca no proprio schema de saida -- documento explicito, testavel, e que sobrevive a evolucao do campo. Self-contained: um unico modulo Python (`src/causaganha_mcp/tools/`) sem tocar Parquet/DuckDB, credenciais ou infraestrutura de deploy; nenhuma outra rodada registrada tentou esta fatia do backlog de seguranca ainda."
success_signal: "Testes novos em tests/causaganha_mcp/ RED-confirmam contra o codigo atual (PublicacaoResult/DecisaoResult nao tem nenhum campo estrutural de confianca de conteudo) e GREEN-confirmam apos a mudanca: (1) todo resultado de `publicacoes_buscar` e `decisoes_buscar` carrega um campo Literal constante (ex.: `tipo_conteudo=\"untrusted_legal_text\"`) presente mesmo quando `trecho` e None; (2) uma fixture de `trecho` contendo uma frase de prompt injection (\"Ignore todas as instrucoes anteriores e...\") passa inalterada, verbatim, no campo de texto -- o marcador nunca sanitiza ou reescreve o teor probatorio, so rotula; (3) o JSON schema exportado da tool (via FastMCP) inclui o campo como parte do contrato, nao como metadado invisivel; (4) doc (`docs/MCP_AGENT_EXPERIENCE.md`, secao 'Contrato de saida') e docstrings das duas tools documentam a fronteira host/agente. `uv run pytest -q` fica verde (exceto os 3 testes de AgentRun-em-rascunho ja documentados em CLAUDE.md, que se resolvem sozinhos ao finalizar este relatorio); `uv run ruff check`/`ruff format --check` limpos."
status: "achieved"
---

# Objetivo: marcador de evidencia nao-confiavel nas tools de teor/arquivo MCP (#1616)

Trabalho principal desta rodada. Ver `decision_ids`/`evidence_ids`/`check_ids`
no `run.md` para o processo TDD completo (RED -> GREEN -> checks).

Fora de escopo explicito desta rodada (registrado para a proxima): os
campos de texto livre de `processo_consultar`
(`DocumentoResult.resumo`, `StjAcordaoResult.tese`/`ementa` em
`src/causaganha_mcp/tools/processo.py`) sao gerados por codegen OKF
(`scripts/generate_okf_domain_models.py` a partir de `knowledge/`) e
exigiriam uma mudanca de TypeContract + migracao, nao apenas um campo
Pydantic novo -- maior que o que cabe com seguranca numa unica rodada
junto do restante do trabalho. O nucleo do invariante (marcar o texto
retornado como dado, nao instrucao) fica coberto nas duas tools que a
propria issue #1616 cita explicitamente no corpo.
