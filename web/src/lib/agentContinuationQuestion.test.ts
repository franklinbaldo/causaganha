import { describe, expect, it } from 'vitest';
import { AGENT_JOB_TOOLS, buildAgentContinuationQuestion } from './agentContinuationQuestion';

describe('buildAgentContinuationQuestion (#1225)', () => {
  it('interpolates exactly the consulted CNJ, masked, with no free interpolation', () => {
    const question = buildAgentContinuationQuestion('0000001-02.2024.8.22.0001');
    expect(question).toContain('0000001-02.2024.8.22.0001');
    // Byte-for-byte reproducible: same input always yields the same output.
    expect(buildAgentContinuationQuestion('0000001-02.2024.8.22.0001')).toBe(question);
  });

  it('uses a different CNJ verbatim when given a different one', () => {
    const question = buildAgentContinuationQuestion('0000002-03.2024.8.22.0002');
    expect(question).toContain('0000002-03.2024.8.22.0002');
    expect(question).not.toContain('0000001-02.2024.8.22.0001');
  });

  it('asks in task language for arquivo, estado and teor, matching the three MCP roles from #1217', () => {
    const question = buildAgentContinuationQuestion('0000001-02.2024.8.22.0001');
    expect(question.toLowerCase()).toContain('arquivo');
    expect(question.toLowerCase()).toContain('estado');
    expect(question.toLowerCase()).toContain('teor');
  });

  it('asks the agent to distinguish absence from unavailability and to report provenance and date', () => {
    const question = buildAgentContinuationQuestion('0000001-02.2024.8.22.0001');
    expect(question.toLowerCase()).toContain('ausência');
    expect(question.toLowerCase()).toContain('indisponibilidade');
    expect(question.toLowerCase()).toContain('proveniência');
    expect(question.toLowerCase()).toContain('data');
  });

  it('never names an internal MCP tool or teaches a JSON payload (#1225 acceptance criteria)', () => {
    const question = buildAgentContinuationQuestion('0000001-02.2024.8.22.0001');
    for (const tool of AGENT_JOB_TOOLS) {
      expect(question).not.toContain(tool);
    }
    expect(question).not.toContain('{');
    expect(question).not.toContain('}');
  });
});
