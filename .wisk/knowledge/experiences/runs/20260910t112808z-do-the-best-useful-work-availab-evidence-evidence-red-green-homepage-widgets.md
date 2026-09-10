---
type: "RunEvidence"
id: "run-evidence/20260910t112808z-do-the-best-useful-work-availab/evidence-red-green-homepage-widgets"
run: "runs/20260910T112808Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "tests/test_generate_homepage_widgets.py"
summary: "scripts/generate_homepage_widgets.py's _discover_parquet_urls() always required a year filter on the manifest's date column (\"AND date LIKE '{year}-%'\") to discover comunicacoes/advogados Parquet URLs. generate_catalog.py's parse_filename() sets date=NULL for the current production consolidated-parquet layout (a bare comunicacoes.parquet/advogados.parquet inside a djen-{tribunal}-{year} IA item, year encoded in ia_item not per file, per docs/CATALOG.md). NULL LIKE '2025-%' is NULL/false in DuckDB, so every current-schema manifest row was silently excluded, leaving com_urls/adv_urls permanently empty and all three homepage widgets (activity_summary, top_tribunais_30d, top_advogados_atividade) permanently empty on the public dashboard, with no error surfaced (only a WARNING log). Fixed by widening the filter to 'date LIKE {year}-% OR ia_item LIKE %-{year}', since ia_item always ends in the 4-digit year for tribunal-year items (_parse_tribunal_year_item enforces MIN_YEAR_CUTOFF<=year<=MAX_YEAR_CUTOFF) and legacy per-day items (djen-YYYY-MM-DD) never end in a bare '-{year}' suffix so the two branches cannot cross-match. RED: 1 of 3 new tests failed on unmodified code (current-layout row returned zero URLs); GREEN: all 3 passed after the fix (current-layout match, year-filter-still-excludes-other-years guard, legacy date-column match all pass)."
goal: "run-goals/20260910t112808z-do-the-best-useful-work-availab/goal-audit-scripts-long-tail"
---

# RunEvidence
