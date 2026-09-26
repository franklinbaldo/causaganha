---
type: AgentGoal
id: "2026-09-25-exciting-mccarthy-xy5a8a-goal-processo-consultar-evidence-marker"
run_id: "2026-09-25-exciting-mccarthy-xy5a8a"
goal: "Estender o marcador tipo_conteudo=untrusted_legal_text a processo_consultar: DocumentoResult.resumo (documentos JURIS/STJ) e StjAcordaoResult.tese/ementa (acordao STJ), fechando o follow-up de #1616 deixado explicito pela PR #1627."
rationale: "PR #1627 fechou o nucleo de #1616 (marcar texto judicial retornado pelo MCP como evidencia nao-confiavel, nunca instrucao) apenas para publicacoes_buscar e decisoes_buscar, deixando processo_consultar como follow-up explicito -- DocumentoResult.resumo e StjAcordaoResult.tese/ementa sao texto judicial pela mesma razao e ficam sem o marcador, quebrando a garantia da matriz de ameacas (TM-11) de que toda superficie que retorna teor carrega o marcador."
success_signal: "Testes novos em tests/causaganha_mcp/test_untrusted_evidence_marker.py provam RED->GREEN: (1) documentos[].tipo_conteudo e stj.tipo_conteudo == UNTRUSTED_LEGAL_TEXT em processo_consultar, mesmo com texto de injecao de prompt passando verbatim; (2) o output_schema publicado pela tool declara tipo_conteudo como const em DocumentoResult e StjAcordaoResult. Suite completa (pytest, ruff, okf-parser check) permanece verde. docs/SECURITY_THREAT_MODEL.md TM-11 e docs/MCP_AGENT_EXPERIENCE.md atualizados para refletir a cobertura das 3 tools. Issue #1616 fechada pela PR."
status: "achieved"
---

# Goal: estender o marcador de evidencia nao-confiavel a processo_consultar

Fechar o follow-up explicito deixado por `#1627`/`#1616`: `resumo`,
`tese` e `ementa` retornados por `processo_consultar` sao texto judicial
com a mesma superficie de risco (prompt injection indireta) ja tratada em
`publicacoes_buscar`/`decisoes_buscar`, mas ainda nao carregavam o
marcador `tipo_conteudo="untrusted_legal_text"`.
