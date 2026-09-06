---
type: AgentEvidence
id: "2026-09-06-exciting-mccarthy-nao666-evidence-924-3-5-consolidation-manifest-live"
run_id: "2026-09-06-exciting-mccarthy-nao666"
goal_id: "2026-09-06-exciting-mccarthy-nao666-goal-close-924-live-verification"
kind: "runtime"
reference: "https://archive.org/download/causaganha-dashboard/consolidation-manifest.json, fetched live 2026-09-06T00:3xZ; src/causaganha/consolidate/schema_registry.py:172 (CURRENT_LAYOUT_REVISION = \"1\"); src/causaganha/consolidate/candidates.py:153-186 (dates_at_current_version/dates_needing_reconsolidation); docs/planning/parquet-storage-optimization-plan.md 'A-rev'/'A1b' rows"
summary: "#924 §3.5 said the real IA archive 'provavelmente tem centenas de itens com layout_revision=\"\"' but this was never measured — a prior round (sf5rj3) tried and got a 404 by looking at the wrong (GitHub Pages) path. The actual publish path is documented in .github/workflows/consolidate-parquet.yml:97-98 as the Internet Archive item `causaganha-dashboard`. Fetched it live (HTTP 200, 43212 bytes) and parsed it: 23 total items, all with schema_version='3.0.0', and ALL 23 (100%) have layout_revision=\"\" — none are yet at CURRENT_LAYOUT_REVISION=\"1\" (dates span 2025-12-18 to 2026-02-12). This is not a hidden bug: the mechanism that would act on it (PR #785's layout_revision field + candidates.py's dates_needing_reconsolidation(), confirmed present and correctly treating '' as stale via unit tests in tests/test_candidates.py) is already shipped and correct — no reconsolidation pass driven by the new layout has ever been run, because the physical layout change it would apply (row-group ORDER BY/size, 'A1' in the storage-optimization plan) is itself still gated on an unrun production benchmark ('A1b... Run against production files before setting a non-default value', still marked '[speculative até medir em produção]'). The real backlog is simply the entire tracked archive (23/23), which is the expected, correct state given A1 has not shipped — not evidence of drift or a missed backfill."
---

# Evidência — #924 §3.5: backlog real do `layout_revision` medido ao vivo

O arquivo publicado real (`consolidation-manifest.json`, via Internet Archive, não GitHub Pages) tem 23/23 itens com `layout_revision=""`. Esperado: o mecanismo (PR #785) está correto e testado, mas nenhuma reconsolidação de layout rodou ainda porque o benchmark de produção que justificaria o novo layout (A1b) ainda não foi executado.
