---
type: AgentEvidence
id: "2026-09-25-exciting-mccarthy-9t0p2a-evidence-red-untrusted-evidence-marker"
run_id: "2026-09-25-exciting-mccarthy-9t0p2a"
kind: "test_red"
reference: "tests/causaganha_mcp/test_untrusted_evidence_marker.py"
summary: "Arquivo de teste novo escrito primeiro contra a API alvo (causaganha_mcp.evidence.UNTRUSTED_LEGAL_TEXT, campo tipo_conteudo em PublicacaoResult/DecisaoResult) que ainda nao existia. `uv run pytest -q tests/causaganha_mcp/test_untrusted_evidence_marker.py` antes de qualquer mudanca de producao falhou na propria coleta do modulo: ModuleNotFoundError: No module named 'causaganha_mcp.evidence' -- confirma que nenhuma forma do marcador estrutural de confianca de conteudo existia no repositorio antes desta mudanca."
---

# Evidencia: RED antes de implementar o marcador de evidencia nao-confiavel (#1616)

```
$ uv run pytest -q tests/causaganha_mcp/test_untrusted_evidence_marker.py
==================================== ERRORS ====================================
___ ERROR collecting tests/causaganha_mcp/test_untrusted_evidence_marker.py ____
ImportError while importing test module '.../tests/causaganha_mcp/test_untrusted_evidence_marker.py'.
Traceback:
tests/causaganha_mcp/test_untrusted_evidence_marker.py:18: in <module>
    from causaganha_mcp.evidence import UNTRUSTED_LEGAL_TEXT
E   ModuleNotFoundError: No module named 'causaganha_mcp.evidence'
=========================== short test summary info ============================
ERROR tests/causaganha_mcp/test_untrusted_evidence_marker.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
```

Confirma que nem `PublicacaoResult` (publicacoes.py) nem `DecisaoResult`
(decisoes.py) tinham qualquer campo estrutural marcando o texto retornado
(`trecho`) como evidencia nao-instrucional antes desta mudanca -- exatamente
o gap que o corpo de `#1616` descreve.
