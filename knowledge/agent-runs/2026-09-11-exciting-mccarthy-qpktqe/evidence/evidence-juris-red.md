---
type: AgentEvidence
id: "2026-09-11-exciting-mccarthy-qpktqe-evidence-juris-red"
run_id: "2026-09-11-exciting-mccarthy-qpktqe"
goal_id: "2026-09-11-exciting-mccarthy-qpktqe-goal-juris-url-percent-encoding-mismatch"
kind: "test_red"
reference: "tests/test_reconcile_processos.py::test_fetch_juris_from_ia_matches_published_juris_url_encoding"
summary: "New test mocks a JURIS IA item whose metadata file listing reports the raw diacritic filename real TJRO uploads use ('2024-01-ACÓRDÃO.parquet'), calls fetch_juris_from_ia(), and asserts the returned URL equals causaganha.decisoes.published.discover_published_juris_datasets's URL for the same (tipo, mes_ano). RED against the unmodified fetch_juris_from_ia: AssertionError, 'https://archive.org/download/tjro-juris-2024/2024-01-ACÓRDÃO.parquet' != 'https://archive.org/download/tjro-juris-2024/2024-01-AC%C3%93RD%C3%83O.parquet' -- the fetch itself succeeds (respx matches the request, which httpx already percent-encoded on the wire), but the stored URL string is the raw, un-encoded form."
---

# RED: mismatch de encoding em fetch_juris_from_ia

Teste falhou contra a implementação original: `fetch_juris_from_ia` armazenava a URL crua (não codificada), divergindo da URL calculada por `published.discover_published_juris_datasets` para o mesmo (tipo, mes_ano).
