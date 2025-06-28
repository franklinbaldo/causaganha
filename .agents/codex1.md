# Agent: codex1

## Profile
- **Name**: codex1
- **Specialization**: Infrastructure & DevEx Specialist
- **Sprint**: sprint-2025-01
- **Branch**: `feat/sprint-2025-01-codex1`
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

### 🟡 In Progress
- [ ] **Ruff configuration optimization** - Fine-tune linting rules for project standards
- [ ] **Pre-commit hooks enhancement** - Add automated testing and documentation checks
- [ ] **GitHub Actions workflow optimization** - Improve CI/CD performance and reliability
- [ ] **VS Code workspace configuration** - Optimal settings for Python development
- [ ] **Docker development environment** - Containerized setup for consistent development

## Task Status Tracking

### Sprint Progress: 0/5 tasks completed

- **Started**: None
- **In Progress**: All tasks assigned
- **Completed**: None
- **Issues**: None

## Deliverables

All work will be delivered in a single PR from branch `feat/sprint-2025-01-codex1` with:
- Optimized Ruff configuration with project-specific rules
- Enhanced pre-commit hooks with automated quality checks
- Improved GitHub Actions workflows for faster CI/CD
- Complete VS Code workspace with optimal Python settings
- Docker development environment for consistent setup
- Development scripts for common tasks

## Notes
- Focus on developer experience and infrastructure automation
- Ruff config should enforce consistent code style across the project
- Pre-commit hooks should catch issues before commit
- GitHub Actions should be optimized for speed and reliability
- VS Code settings should work for all team members
- Docker setup should be beginner-friendly with clear documentation