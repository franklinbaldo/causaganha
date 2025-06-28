# Agent Registry

This directory contains the agent registry for CausaGanha parallel development.

## Current Sprint: sprint-2025-03

### Active Agents (19/19)

| Agent | Specialization | Branch | Tasks | Status |
|-------|---------------|--------|-------|--------|
| [testing-docs](./testing-docs.md) | Testing & Documentation | `feat/sprint-2025-03-testing-docs` | 0/5 ⬜ | Active |
| [quality-docs](./quality-docs.md) | Quality & Documentation | `feat/sprint-2025-03-quality-docs` | 0/5 ⬜ | Active |
| [infrastructure-devex](./infrastructure-devex.md) | Infrastructure & DevEx | `feat/sprint-2025-03-infrastructure-devex` | 0/5 ⬜ | Active |
| [monitoring-integration](./monitoring-integration.md) | Monitoring & Integration | `feat/sprint-2025-03-monitoring-integration` | 0/5 ⬜ | Active |
| [roberta-vieira](./roberta-vieira.md) | Otimização de modelos LLM e Pydantic | `feat/sprint-2025-03-roberta-vieira` | 0/5 ⬜ | Active |
| [kenji-nakamura](./kenji-nakamura.md) | Automação de pipelines assíncronos | `feat/sprint-2025-03-kenji-nakamura` | 0/5 ⬜ | Active |
| [sophie-dubois](./sophie-dubois.md) | Governança de dados e GDPR | `feat/sprint-2025-03-sophie-dubois` | 0/5 ⬜ | Active |
| [amit-sharma](./amit-sharma.md) | Arquitetura distribuída DuckDB | `feat/sprint-2025-03-amit-sharma` | 0/5 ⬜ | Active |
| [anna-muller](./anna-muller.md) | Observabilidade e monitoramento | `feat/sprint-2025-03-anna-muller` | 0/5 ⬜ | Active |
| [juan-carlos](./juan-carlos.md) | CLI e experiência do desenvolvedor | `feat/sprint-2025-03-juan-carlos` | 0/5 ⬜ | Active |
| [sara-nilsson](./sara-nilsson.md) | Testes de performance e custos | `feat/sprint-2025-03-sara-nilsson` | 0/5 ⬜ | Active |
| [dimitri-ivanov](./dimitri-ivanov.md) | Segurança em sistemas distribuídos | `feat/sprint-2025-03-dimitri-ivanov` | 0/5 ⬜ | Active |
| [liu-wei](./liu-wei.md) | Processamento de dados multilíngue | `feat/sprint-2025-03-liu-wei` | 0/5 ⬜ | Active |
| [nora-khaled](./nora-khaled.md) | Arquivamento digital legal | `feat/sprint-2025-03-nora-khaled` | 0/5 ⬜ | Active |
| [clara-alves](./clara-alves.md) | Product Owner | `feat/sprint-2025-03-clara-alves` | 0/5 ⬜ | Active |
| [fernando-costa](./fernando-costa.md) | Project Manager | `feat/sprint-2025-03-fernando-costa` | 0/5 ⬜ | Active |
| [lucas-ribeiro](./lucas-ribeiro.md) | Tech Lead | `feat/sprint-2025-03-lucas-ribeiro` | 0/5 ⬜ | Active |
| [elena-rossi](./elena-rossi.md) | UX Researcher | `feat/sprint-2025-03-elena-rossi` | 0/5 ⬜ | Active |
| [bruno-silva](./bruno-silva.md) | Code Quality & Refactoring | `feat/sprint-2025-03-bruno-silva` | 0/5 ⬜ | Active |

## Sprint Overview

- **Sprint ID**: sprint-2025-03
- **Duration**: 2-3 weeks (estimated)
- **Total Tasks**: 0/95 completed ⬜ (0% progress)
- **File Conflicts**: Zero (strict file boundaries enforced)
- **Delivery Method**: Single PR per agent at sprint end

## File Zone Summary

```
testing-docs:   tests/test_extractor.py, tests/test_ia_discovery.py, tests/benchmarks/, docs/api/, docs/tutorials/
quality-docs:   tests/mock_data/, tests/test_error_simulation.py, docs/diagrams/, docs/faq.md, docs/examples/
infrastructure-devex:   ruff.toml, .pre-commit-config.yaml, .github/workflows/, .vscode/, Docker*, scripts/
monitoring-integration:  src/ (type hints), src/utils/logging_config.py, scripts/{dev,db,env}/, .env.example
roberta-vieira:         (unassigned)
kenji-nakamura:         (unassigned)
sophie-dubois:          (unassigned)
amit-sharma:            (unassigned)
anna-muller:            (unassigned)
juan-carlos:            (unassigned)
sara-nilsson:           (unassigned)
dimitri-ivanov:         (unassigned)
liu-wei:                (unassigned)
nora-khaled:            (unassigned)
clara-alves:           (unassigned)
fernando-costa:        (unassigned)
lucas-ribeiro:         (unassigned)
elena-rossi:           (unassigned)
bruno-silva:          (unassigned)
```

## Agent Coordination

1. **File Boundaries**: Strict enforcement to prevent merge conflicts
2. **Single PR Delivery**: Each agent delivers all work in one comprehensive PR
3. **Sprint Branches**: Named `feat/sprint-2025-03-{agent-name}`
4. **Status Tracking**: Individual agent files track progress
5. **Quality Standards**: All work must include tests and documentation

## Next Sprint

Sprint `sprint-2025-03` focuses on multi-tribunal infrastructure, validation and
expanded documentation.

## Usage & Communication

### **Sprint Workflow**
Each agent should:
1. Read their individual `.md` file for assignments
2. Create their sprint branch
3. Work within assigned file boundaries
4. Update progress in their agent file
5. Deliver all work in a single PR at sprint end

### **Agent Communication Guidelines**
- **Card Permissions**: You may freely modify your entire agent card as a scratchpad
- **Questions & Suggestions**: You can ask questions in your card's scratchpad section about:
  - Future tasks or sprint planning
  - Project architecture suggestions
  - Process improvements
  - Technical recommendations
- **What NOT to ask**: Questions about current task implementation details (work autonomously on assigned deliverables)
- **Response Method**: Questions will be answered directly in your card using Wikipedia-style signatures
- **Collaboration**: Feel free to suggest cross-agent collaboration opportunities
- **Board Messaging**: Use `.BOARD/` messages for cross-agent communication and never edit another agent's card

