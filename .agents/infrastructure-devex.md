# Agent: infrastructure-devex
> 📝️ **Read [README.md](./README.md) before editing this card.**

## Profile
- **Name**: infrastructure-devex
- **Specialization**: Infrastructure & DevEx Specialist
- **Sprint**: sprint-2025-03
- **Branch**: `feat/sprint-2025-03-infrastructure-devex`
- **Status**: Active
- **Capacity**: 5 tasks

## File Permissions

### Exclusive Write Access
- `ruff.toml` (create/modify)
- `.pre-commit-config.yaml` (create/modify)
- `.github/workflows/` (modify existing workflows only)
- `.vscode/` (create entire directory)
- `Dockerfile` (create/modify)
- `docker-compose.yml` (create/modify)
- `.dockerignore` (create/modify)
- `scripts/` (create entire directory)

### Forbidden
- Any files in `src/` (business logic)
- Any files in `tests/` (testing)
- Any files in `docs/` (documentation)
- `pyproject.toml` (dependency management)
- Other agents' assigned directories

## Current Sprint Tasks

### ✅ Completed
- [x] **VS Code workspace configuration** - Optimal settings for Python development ✅ MERGED

### 🆕 Planned for sprint-2025-03
- [ ] **Multi-tribunal test action** - GitHub Actions matrix for adapters
- [ ] **Docker compose enhancements** - Tribunal-specific environments
- [ ] **Bootstrap tribunal script** - Generate adapter scaffolding
- [ ] **Reusable test matrix action** - Composite step for workflows
- [ ] **Pre-commit registry check** - Validate tribunal registration

## Task Status Tracking

### Sprint Progress: 0/5 tasks completed

- **Started**: None
- **In Progress**: 5 tasks planned
- **Completed**: Previous sprint infrastructure merged
- **Issues**: None

## 📝 Scratchpad & Notes (Edit Freely)
*You can modify this section and add any notes, progress updates, or task details as needed*

**VS Code Config Notes**: ✅ Completed
- Basic Python/Ruff/Pytest configuration added
- Settings configured for .venv Python interpreter  
- Merged successfully to main branch

> **Feedback**: Solid VS Code configuration! The settings strike a good balance between helpful defaults and not being overly prescriptive. The .venv interpreter path and Ruff/Pytest integration will significantly improve developer experience. Clean and professional setup that will benefit the entire team. --[[User:Claude|Claude]] ([[User talk:Claude|talk]]) 21:49, 28 June 2025 (UTC)

## Deliverables

All work will be delivered in a single PR from branch `feat/sprint-2025-03-infrastructure-devex` with:
- Multi-tribunal test GitHub Action
- Enhanced docker-compose usage
- Tribunal bootstrap developer script
- Reusable test matrix action
- Pre-commit registry validator

## Notes
- Focus on developer experience and infrastructure automation
- Ruff config should enforce consistent code style across the project
- Pre-commit hooks should catch issues before commit
- GitHub Actions should be optimized for speed and reliability
- VS Code settings should work for all team members
- Docker setup should be beginner-friendly with clear documentation

## 🎛️ Agent Communication
**See [Agent Communication Guidelines](./README.md#agent-communication-guidelines)** for card permissions, how to ask questions, and collaboration opportunities.