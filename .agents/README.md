# Agent Registry

This directory contains the agent registry for CausaGanha parallel development.

## Current Sprint: sprint-2025-02

### Active Agents (7/7)

| Agent | Specialization | Branch | Tasks | Status |
|-------|---------------|--------|-------|--------|
| [jules1](./jules1.md) | Testing & Documentation | `feat/sprint-2025-02-jules1` | 0/5 ⬜ | Active |
| [jules2](./jules2.md) | Quality & Documentation | `feat/sprint-2025-02-jules2` | 0/5 ⬜ | Active |
| [codex1](./codex1.md) | Infrastructure & DevEx | `feat/sprint-2025-02-codex1` | 0/5 ⬜ | Active |
| [gemini1](./gemini1.md) | Monitoring & Integration | `feat/sprint-2025-02-gemini1` | 0/5 ⬜ | Active |
| [techlead1](./techlead1.md) | Technical Lead | `feat/sprint-2025-02-techlead1` | 0/0 ⬜ | Active |
| [pm1](./pm1.md) | Product Management | `feat/sprint-2025-02-pm1` | 0/0 ⬜ | Active |
| [flowlead1](./flowlead1.md) | Flow Leader | `feat/sprint-2025-02-flowlead1` | 0/0 ⬜ | Active |

## Sprint Overview

- **Sprint ID**: sprint-2025-02
- **Duration**: 2-3 weeks (estimated)
- **Total Tasks**: 0/20 completed ⬜ (0% progress)
- **File Conflicts**: Zero (strict file boundaries enforced)
- **Delivery Method**: Single PR per agent at sprint end

## File Zone Summary

```
jules1:   tests/test_extractor.py, tests/test_ia_discovery.py, tests/benchmarks/, docs/api/, docs/tutorials/
jules2:   tests/mock_data/, tests/test_error_simulation.py, docs/diagrams/, docs/faq.md, docs/examples/
codex1:   ruff.toml, .pre-commit-config.yaml, .github/workflows/, .vscode/, Docker*, scripts/
gemini1:  src/ (type hints), src/utils/logging_config.py, scripts/{dev,db,env}/, .env.example
techlead1:  entire repository (coordination only), agent card notes
pm1:        docs/plans/
flowlead1:  .agents/
```

## Agent Coordination

1. **File Boundaries**: Strict enforcement to prevent merge conflicts
2. **Single PR Delivery**: Each agent delivers all work in one comprehensive PR
3. **Sprint Branches**: Named `feat/sprint-2025-02-{agent-name}`
4. **Status Tracking**: Individual agent files track progress
5. **Quality Standards**: All work must include tests and documentation

## Next Sprint

Sprint `sprint-2025-02` is now active with a focus on analytics, monitoring and
external integration improvements.

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