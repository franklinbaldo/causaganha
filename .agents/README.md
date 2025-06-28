# Agent Registry

This directory contains the agent registry for CausaGanha parallel development.

## Current Sprint: sprint-2025-01

### Active Agents (4/4)

| Agent | Specialization | Branch | Tasks | Status |
|-------|---------------|--------|-------|--------|
| [jules1](./jules1.md) | Testing & Documentation | `feat/sprint-2025-01-jules1` | 2/5 ✅ | Active |
| [jules2](./jules2.md) | Quality & Documentation | `feat/sprint-2025-01-jules2` | 1/5 ✅ | Active |
| [codex1](./codex1.md) | Infrastructure & DevEx | `feat/sprint-2025-01-codex1` | 1/5 ✅ | Active |
| [gemini1](./gemini1.md) | Monitoring & Integration | `feat/sprint-2025-01-gemini1` | 1/5 ✅ | Active |

## Sprint Overview

- **Sprint ID**: sprint-2025-01
- **Duration**: 2-3 weeks (estimated)
- **Total Tasks**: 5/20 completed ✅ (25% progress)
- **File Conflicts**: Zero (strict file boundaries enforced)  
- **Delivery Method**: Single PR per agent at sprint end

## File Zone Summary

```
jules1:   tests/test_extractor.py, tests/test_ia_discovery.py, tests/benchmarks/, docs/api/, docs/tutorials/
jules2:   tests/mock_data/, tests/test_error_simulation.py, docs/diagrams/, docs/faq.md, docs/examples/
codex1:   ruff.toml, .pre-commit-config.yaml, .github/workflows/, .vscode/, Docker*, scripts/
gemini1:  src/ (type hints), src/utils/logging_config.py, scripts/{dev,db,env}/, .env.example
```

## Agent Coordination

1. **File Boundaries**: Strict enforcement to prevent merge conflicts
2. **Single PR Delivery**: Each agent delivers all work in one comprehensive PR
3. **Sprint Branches**: Named `feat/sprint-2025-01-{agent-name}`
4. **Status Tracking**: Individual agent files track progress
5. **Quality Standards**: All work must include tests and documentation

## Next Sprint

Available for assignment:
- Analytics & Monitoring tasks (5)
- External Integration tasks (5)

## Usage

Each agent should:
1. Read their individual `.md` file for assignments
2. Create their sprint branch
3. Work within assigned file boundaries
4. Update progress in their agent file
5. Deliver all work in a single PR at sprint end