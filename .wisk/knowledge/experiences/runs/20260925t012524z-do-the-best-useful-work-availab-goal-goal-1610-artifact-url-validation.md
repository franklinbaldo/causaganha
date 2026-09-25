---
goal: "Fechar issue #1610 (validar URLs de manifesto/proveniência antes do DuckDB) para src/causaganha/processos/service.py: nenhum read_parquet recebe arquivo_ia_url do índice sem passar por um validador central que falha fechado (https-only, host archive.org, path /download/*.parquet, sem query/fragment/aspas)."
id: "run-goals/20260925t012524z-do-the-best-useful-work-availab/goal-1610-artifact-url-validation"
kind: "task-advance"
rationale: "É uma vulnerabilidade real e concreta (SQL/URL injection via manifesto comprometido, achada na auditoria de threat model de 2026-09-24), testável por pytest puro sem depender de credencial nenhuma -- avanço real e imediatamente entregável nesta rodada, ao contrário do handoff #1471 (bloqueado)."
run: "runs/20260925T012524Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "12 testes novos GREEN (11 unitários de _validate_artifact_url cobrindo host estranho/http/file/query/fragment/aspas/path fora do padrão + 1 de integração mostrando degradação graciosa via aviso) e suíte completa do repositório (uv run pytest -q) verde; PR aberto contra main referenciando #1610."
type: "RunGoal"
---

# RunGoal
