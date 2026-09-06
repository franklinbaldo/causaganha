/**
 * "Continuar com um agente" (issue #1225): a single, testable authority for
 * the natural-language question `/processo` offers to copy once a CNJ lookup
 * lands on `found`, so a person can hand the same already-consulted CNJ to a
 * connected agent instead of retyping it after navigating to `/agentes`.
 *
 * The wording deliberately mirrors the task-language convention the #1217
 * example questions on `/agentes` established (causaganha_mcp/agents_examples.py):
 * no MCP tool name, no JSON payload, and an explicit ask to distinguish
 * absence from unavailability and to report each source's provenance/date —
 * the same guarantees `/processo` itself already surfaces for a human reader.
 * A verbatim cross-language contract test is not applicable here (unlike
 * #1217's static page), because the CNJ is a runtime value the user typed,
 * not a fixed golden fixture.
 */

// The four MCP tools /agentes documents (#1217/#1219) — kept here only so
// tests can assert the copied question never leaks an internal tool name.
export const AGENT_JOB_TOOLS = [
  'processo_consultar',
  'publicacoes_buscar',
  'processo_estado',
  'decisoes_buscar',
] as const;

export function buildAgentContinuationQuestion(nrProcessoMascara: string): string {
  return (
    `Analise o processo ${nrProcessoMascara} no CausaGanha: consulte arquivo, estado e teor ` +
    'disponíveis, diferencie ausência de indisponibilidade e informe a proveniência e a data de cada fonte.'
  );
}
