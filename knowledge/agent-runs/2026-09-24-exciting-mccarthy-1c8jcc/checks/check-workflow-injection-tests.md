---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-1c8jcc-check-workflow-injection-tests"
run_id: "2026-09-24-exciting-mccarthy-1c8jcc"
command: "uv run pytest -q tests/test_workflow_dispatch_injection.py"
result: "passed"
summary: "49 passed apos a correcao. Ver evidence-red-pytest para a mesma suite rodada contra o conteudo pre-fix (git stash) e evidence-green-pytest para o resultado final."
---

# Check: suite de regressao de injecao via workflow_dispatch

```
$ uv run pytest -q tests/test_workflow_dispatch_injection.py
...............................................                          [100%]
49 passed
```
