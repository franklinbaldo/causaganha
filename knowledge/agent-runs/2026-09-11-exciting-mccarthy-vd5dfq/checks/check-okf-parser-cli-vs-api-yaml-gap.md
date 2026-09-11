---
type: AgentCheck
id: "2026-09-11-exciting-mccarthy-vd5dfq-check-okf-parser-cli-vs-api-yaml-gap"
run_id: "2026-09-11-exciting-mccarthy-vd5dfq"
goal_id: "2026-09-11-exciting-mccarthy-vd5dfq-goal-datajud-timezone-date-shift"
command: "uv run okf-parser check knowledge --relational-schema okf.schema.sql; uv run python -c \"from pathlib import Path; from okf_parser import load_bundle; print(load_bundle(Path('knowledge')).is_conformant)\""
result: "observed"
summary: "This round's own reading-okf.md had an invalid double-quoted YAML frontmatter scalar (an embedded blank line breaking quoted-scalar folding, byte 377 line 6). `uv run okf-parser check knowledge --relational-schema okf.schema.sql` reported {conformant: true, diagnostics: []} with the bad file present -- a false negative. Directly calling the Python API src.causaganha_mcp.knowledge.py itself depends on (`okf_parser.load_bundle(Path('knowledge')).is_conformant`) correctly caught it: `is_conformant=False`, one OKF001/ERROR diagnostic naming the exact file/line/column. This is exactly the check that then made `uv run pytest -q` fail 14 tests in tests/causaganha_mcp/ (test_causaganha_status.py, test_okf_pipeline_catalog.py, test_status_contract.py) with 'RuntimeError: knowledge bundle is not OKF-conformant' once the bad file existed -- i.e. the CLI `check` subcommand this scaffold instructs every round to run as its primary validation loop did NOT surface a real, test-suite-breaking conformance error that the production code path does enforce. Root-caused and fixed by removing the invalid blank line inside the finding field's quoted scalar (joining two paragraphs into one continuous string); re-ran both after the fix: CLI reports conformant=true (unchanged, so it was never sensitive to this), and load_bundle().is_conformant is now also True, with the full pytest suite passing 100% including all 14 previously-failing tests."
---

# Check: lacuna entre `okf-parser check` (CLI) e `load_bundle().is_conformant` (API)

O `reading-okf.md` desta rodada tinha um scalar YAML quoted inválido (linha em branco embutida). O comando `okf-parser check` do scaffold reportou `conformant: true` mesmo assim (falso negativo); a API Python que `causaganha_mcp.knowledge.load_pipeline_metadata` realmente usa (`load_bundle(...).is_conformant`) capturou corretamente o erro, o que derrubava 14 testes em `tests/causaganha_mcp/`. Corrigido removendo a linha em branco dentro do scalar. Suíte completa volta a 100% verde após a correção.
