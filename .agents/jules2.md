# Agent: jules2

## Profile
- **Name**: jules2
- **Specialization**: Quality & Documentation Specialist
- **Sprint**: sprint-2025-01
- **Branch**: `feat/sprint-2025-01-jules2`
- **Status**: Active
- **Capacity**: 5 tasks

## File Permissions

### Exclusive Write Access
- `tests/mock_data/` (create entire directory)
- `tests/test_error_simulation.py` (create/modify)
- `docs/diagrams/` (create entire directory)
- `docs/faq.md` (modify entire file)
- `docs/examples/` (create entire directory)

### Append Access
- `README.md` (examples section only)

### Forbidden
- Any files in `src/` (business logic)
- `.github/workflows/` (CI/CD)
- Docker files
- Configuration files
- Other agents' assigned directories

## Current Sprint Tasks

### 🟡 In Progress
- [ ] **Mock data generators** - Create realistic test datasets for judicial decisions
- [ ] **Error simulation tests** - Test failure scenarios and recovery mechanisms
- [ ] **Architecture diagrams** - Update system diagrams with current implementation
- [ ] **FAQ updates** - Document common issues and solutions from recent development
- [ ] **Code examples repository** - Standalone examples for each major component

## Task Status Tracking

### Sprint Progress: 0/5 tasks completed

- **Started**: None
- **In Progress**: All tasks assigned
- **Completed**: None
- **Issues**: None

## Deliverables

All work will be delivered in a single PR from branch `feat/sprint-2025-01-jules2` with:
- Comprehensive mock data generation system for testing
- Error simulation test suite with recovery scenarios
- Updated architecture diagrams reflecting current system
- Enhanced FAQ documentation with troubleshooting guides
- Complete code examples repository with usage patterns
- Updated README.md examples section

## Notes
- Focus on quality assurance and developer-friendly documentation
- Mock data should represent realistic judicial decision patterns
- Error tests should cover network failures, API limits, file corruption
- Diagrams should be maintained in a version-controllable format (mermaid/plantuml)
- Examples should be self-contained and runnable