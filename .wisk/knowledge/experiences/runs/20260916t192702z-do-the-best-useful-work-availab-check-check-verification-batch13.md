---
type: "RunCheck"
id: "run-checks/20260916t192702z-do-the-best-useful-work-availab/check-verification-batch13"
run: "runs/20260916T192702Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run pytest -q tests/segmenter_dataset/test_segmenter_governance_status.py -k batch13; uv run pytest -q tests/segmenter_dataset/; uv run ruff check .; uv run ruff format --check .; uv run python scripts/segmenter_semantic_audit.py --store data/segmenter; uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs; uv run pytest -q tests/knowledge/test_backlog.py; uv run okf-parser check knowledge --relational-schema okf.schema.sql"
result: "test_real_store_reflects_batch13_corpus_growth passou (GREEN). Suite completa tests/segmenter_dataset/ passou (389 testes, exit 0). ruff check/format limpos (450 arquivos). Audit semantico sem novos achados para os 5 documentos novos (os 9 achados pre-existentes nao mudaram). check_agent_run_completeness.py limpo. tests/knowledge/test_backlog.py verde (7 testes, incluindo a resolucao de last_verified_run_id com prefixo wisk:). okf-parser check conformant (1930 concepts, 0 diagnostics). PR #1567 aberto, CI disparada (CodeQL x4 em andamento, sem falhas ate agora); uv run pytest -q completo (repo inteiro) tambem disparado em background para confirmacao final antes do fechamento do relatorio."
status: "pass"
evidence: "run-evidence/20260916t192702z-do-the-best-useful-work-availab/evidence-batch13-ingested"
goal: "run-goals/20260916t192702z-do-the-best-useful-work-availab/goal-segmenter-batch13"
---

# RunCheck
