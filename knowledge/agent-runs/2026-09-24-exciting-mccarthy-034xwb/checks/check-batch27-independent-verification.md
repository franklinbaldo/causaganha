---
type: AgentCheck
id: "2026-09-24-exciting-mccarthy-034xwb-check-batch27-independent-verification"
run_id: "2026-09-24-exciting-mccarthy-034xwb"
goal_id: "2026-09-24-exciting-mccarthy-034xwb-goal-batch27-corpus-growth"
command: "uv run ruff check; uv run ruff format --check; uv run python scripts/segmenter_governance_status.py; uv run python scripts/segmenter_semantic_audit.py; uv run pytest -q tests/segmenter_dataset; verbatim-fidelity diff script (inline python)"
result: "pass"
evidence_id: "2026-09-24-exciting-mccarthy-034xwb-evidence-batch27-ingested"
---

# Check: reverificacao independente do lote 27

Rodado por esta sessao apos o agente em background reportar o lote
27 concluido, sem confiar apenas no autorrelato. `ruff check`/`format
--check` limpos; `segmenter_governance_status.py` confirma
`document_count=195`; `segmenter_semantic_audit.py` confirma zero
achados novos alem da allowlist de 7; `pytest -q
tests/segmenter_dataset` 100% verde (251 testes); script inline de
diff confirma `EXACT MATCH` byte-a-byte entre o texto tageado (tags
removidas) e o `texto_limpo` original para os dois novos documentos.
