---
type: "RunEvidence"
id: "run-evidence/20260914t132556z-do-the-best-useful-work-availab/evidence-live-runtime-verification"
run: "runs/20260914T132556Z-do-the-best-useful-work-available-in-this-reposi"
kind: "execution"
reference: "https://archive.org/download/djen-tjro-2025/comunicacoes.parquet"
summary: "Manually ran the implemented functions against real production archive.org data (outside pytest, ephemeral scratch scripts, no files kept): list_djen_items() against the live advancedsearch.php endpoint returned 771 raw identifier:djen-* matches, filtered by is_tribunal_year_item() down to 155 current djen-{tribunal}-{year} items (excluding legacy djen-YYYY-MM-DD per-day items, per CLAUDE.md's documented naming migration). read_footer_stats() + classify_file() against djen-tjro-2025's real comunicacoes.parquet (1,634,023 rows, 14 row groups) correctly read its actual KV metadata (causaganha.schema_version=3.0.0, causaganha.item_id=djen-tjro-2025, no layout marker) and classified it reorder_candidate -- matching the real-world expectation that this file predates PR #1473's CNJ-first ordering and is not yet sorted by numero_processo."
goal: "run-goals/20260914t132556z-do-the-best-useful-work-availab/goal-audit-cnj-parquets"
---

# RunEvidence
