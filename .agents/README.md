# Agent Registry

This directory contains the agent registry for CausaGanha parallel development.

## Current Sprint: sprint-2025-03

### Active Agents (5/5)

| Agent | Specialization | Branch | Tasks | Status |
|-------|---------------|--------|-------|--------|
| [quality-docs](./quality-docs.md) | Quality & Documentation | `feat/sprint-2025-03-quality-docs` | 0/5 ⬜ | Active |
| [infrastructure-devex](./infrastructure-devex.md) | Infrastructure & DevEx | `feat/sprint-2025-03-infrastructure-devex` | 0/5 ⬜ | Active |
| [monitoring-integration](./monitoring-integration.md) | Monitoring & Integration | `feat/sprint-2025-03-monitoring-integration` | 0/5 ⬜ | Active |
| [roberta-vieira](./roberta-vieira.md) | Otimização de modelos LLM e Pydantic | `feat/sprint-2025-03-roberta-vieira` | 0/5 ⬜ | Active |
| [bruno-silva](./bruno-silva.md) | Code Quality & Refactoring | `feat/sprint-2025-03-bruno-silva` | 0/5 ⬜ | Active |

## Sprint Overview

- **Sprint ID**: sprint-2025-03
- **Duration**: 2-3 weeks (estimated)
- **Total Tasks**: 0/25 completed ⬜ (0% progress)
- **File Conflicts**: Zero (strict file boundaries enforced)
- **Delivery Method**: Single PR per agent at sprint end

## File Zone Summary

```
quality-docs:   tests/mock_data/, tests/test_error_simulation.py, docs/diagrams/, docs/faq.md, docs/examples/
infrastructure-devex:   ruff.toml, .pre-commit-config.yaml, .github/workflows/, .vscode/, Docker*, scripts/
monitoring-integration:  src/ (type hints), src/utils/logging_config.py, scripts/{dev,db,env}/, .env.example
roberta-vieira:         (unassigned)
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

