---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-zrek2s-evidence-nbsp-strip-bug-fixed"
run_id: "2026-09-16-exciting-mccarthy-zrek2s"
kind: "test_green"
reference: "tests/segmenter_dataset/test_ingest_djen_sample_technique1_batch.py::test_ingest_preserves_leading_nbsp_and_blank_lines, scripts/ingest_djen_sample_technique1_batch.py"
summary: "RED->GREEN: str.strip() em _parse_tagged tratava U+00A0 (NBSP) como whitespace e descartava silenciosamente conteudo real no inicio/fim do texto-fonte, causando um falso mismatch de fidelidade verbatim (achado ao vivo no candidato TJGO 543565881, diff programatico confirmou delete de '\\xa0\\n\\n\\n\\n\\n\\n' na posicao 0). Corrigido para tagged_text.strip('\\n\\r\\t ') com teste de regressao."
---

# Evidencia: bug de strip() com NBSP corrigido (RED -> GREEN)

## RED

```
uv run pytest tests/segmenter_dataset/test_ingest_djen_sample_technique1_batch.py::test_ingest_preserves_leading_nbsp_and_blank_lines -q
...
AssertionError: assert {'doc6': 'ver...en 65 vs 69)'} == {}
```

## Diagnostico ao vivo (candidato real do lote 7, TJGO 543565881)

```python
sm = difflib.SequenceMatcher(None, source, reconstructed)
# delete '\xa0\n\n\n\n\n\n' -> '' at 0 0
```

`source` (13487 chars) vs `reconstructed` (13480 chars) -- diferenca
exatamente os 7 caracteres do prefixo `\xa0\n\n\n\n\n\n`, removidos pelo
`tagged_text.strip()` da funcao `_parse_tagged` antes do parse XML,
porque `"\xa0".isspace()` e `True` em Python.

## Fix

`scripts/ingest_djen_sample_technique1_batch.py`, `_parse_tagged`:

```python
stripped = tagged_text.strip("\n\r\t ")
root = ET.fromstring(f"<text>{stripped}</text>")
```

## GREEN

```
uv run pytest tests/segmenter_dataset/test_ingest_djen_sample_technique1_batch.py -q
........                                                                 [100%]
uv run ruff check / ruff format --check: limpos
```

Apos o fix, o candidato real TJGO 543565881 ingeriu sem erro de
fidelidade verbatim (confirmado em `evidence-batch7-ingested`).
