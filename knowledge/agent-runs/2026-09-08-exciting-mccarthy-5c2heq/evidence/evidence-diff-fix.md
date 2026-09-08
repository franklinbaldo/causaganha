---
type: AgentEvidence
id: "2026-09-08-exciting-mccarthy-5c2heq-evidence-diff-fix"
run_id: "2026-09-08-exciting-mccarthy-5c2heq"
goal_id: "2026-09-08-exciting-mccarthy-5c2heq-goal-calendar-json-status-vocabulary"
kind: "diff"
reference: "scripts/generate_cache_from_manifest.py (generate_calendar_json + new _calendar_bucket helper); tests/test_generate_cache_from_manifest.py (new file)"
summary: "git diff --stat: 1 file changed, 21 insertions(+), 6 deletions(-) in scripts/generate_cache_from_manifest.py, plus one new test file. Adds _calendar_bucket(row) classifying ia_status='uploaded' -> uploaded, djen_status in ('available','confirmed') -> pending, djen_status='absent' -> absent, else -> unknown -- the same four-way vocabulary totals.qmd/tribunal_coverage.qmd use. generate_calendar_json's by_date accumulator now tracks all four buckets (was uploaded/absent/total only) and each day's output now includes pending and unknown alongside the existing uploaded/absent/total/coverage_pct fields, so uploaded+pending+absent+unknown always equals total."
---

# Evidencia: diff da correcao

`_calendar_bucket()` novo, `generate_calendar_json` migrado para os quatro buckets. `git diff --stat`: 21 insercoes, 6 remocoes em `scripts/generate_cache_from_manifest.py`, mais um arquivo de teste novo.
