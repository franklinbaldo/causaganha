---
type: "RunCheck"
id: "run-checks/20260925t012524z-do-the-best-useful-work-availab/check-verification-pytest-full-suite"
run: "runs/20260925T012524Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q (suíte completa do repositório) e uv run pytest tests/causaganha/processos/test_service.py -q (módulo alvo, isolado); uv run ruff check src/causaganha/processos/service.py tests/causaganha/processos/test_service.py; uv run ruff format --check (mesmo escopo)."
result: "Módulo alvo: 31 passed. Suíte completa: green, exit code 0 (todas as fases de porcentagem 0%-100% sem F/E). ruff check: All checks passed. ruff format --check: limpo após um auto-reformat de uma linha (if multi-linha do path-suffix), sem mudança de semântica."
status: "pass"
evidence: "evidence-1610-artifact-url-validation"
goal: "goal-1610-artifact-url-validation"
---

# RunCheck
