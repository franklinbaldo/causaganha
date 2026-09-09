---
type: AgentEvidence
id: "2026-09-09-exciting-mccarthy-0lpi0s-evidence-ci-fix-vulture"
run_id: "2026-09-09-exciting-mccarthy-0lpi0s"
goal_id: "2026-09-09-exciting-mccarthy-0lpi0s-goal-fixture-network-guard"
kind: "ci"
reference: "PR #1358, 'lint' check run 102328892805 (head 4c57ab6), https://github.com/franklinbaldo/causaganha/actions/runs/34308095055"
summary: "PR #1358's 'lint' CI check failed twice (both pushed commits) on `uvx vulture src/ scripts/ vulture_whitelist.py --min-confidence 100`, exit code 3: 'scripts/render_contract_fixture.py:76: unused variable 'kwargs' (100% confidence)' and same at line 80 -- the *args/**kwargs catch-alls on _blocked_urlopen/_blocked_send were never read in the body (they exist only so the blocked functions accept whatever real call signature they replace). Reproduced locally with `uvx vulture src/ scripts/ vulture_whitelist.py --min-confidence 100` (not run during this goal's earlier local verification -- an omission, not a flake: `uv run ruff check`/`pytest` don't invoke vulture, so nothing local caught this before the push). Fixed by renaming the unused parameters to _args/_kwargs/_self (vulture ignores underscore-prefixed names, confirmed locally: a minimal repro function with *_args, **_kwargs exits 0). Re-ran locally pinned to Python 3.13 (`uvx --python 3.13 vulture ...`) to match CI's Python 3.12 runner -- the unpinned default in this sandbox is Python 3.11, which cannot even parse src/stj_acordaos/client.py's/src/tjro_juris/client.py's PEP 695 generic function syntax and produces unrelated parse errors that do not occur on 3.12+ (a local-sandbox artifact, not a real finding): exit 0, no findings."
---

# Evidência: correção do CI (lint/vulture)

O check `lint` falhou por parâmetros `*args, **kwargs` nunca lidos em `_blocked_urlopen`/`_blocked_send`. Corrigido renomeando para `_args`/`_kwargs`/`_self` (convenção que o `vulture` já ignora). Reproduzido e confirmado localmente, fixado no Python 3.13 para bater com o runner de CI (o Python 3.11 padrão deste sandbox nem consegue parsear a sintaxe de generics PEP 695 já existente em outros arquivos do repo).
