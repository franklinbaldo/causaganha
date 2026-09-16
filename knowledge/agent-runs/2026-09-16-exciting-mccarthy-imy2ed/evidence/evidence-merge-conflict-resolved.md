---
type: AgentEvidence
id: "2026-09-16-exciting-mccarthy-imy2ed-evidence-merge-conflict-resolved"
run_id: "2026-09-16-exciting-mccarthy-imy2ed"
goal_id: "2026-09-16-exciting-mccarthy-imy2ed-goal-djen-sample-batch10"
kind: "diff"
reference: "knowledge/backlog/issue-1050.md, tests/segmenter_dataset/test_segmenter_governance_status.py, tests/segmenter_dataset/test_segmenter_audit_scripts.py"
summary: "git merge origin/main conflicted on issue-1050.md and test_segmenter_governance_status.py (both batch9/hv2ep2 and batch10/imy2ed edited the same prose and added a risk class numbered 7). Resolved by keeping both rounds' content, renumbering imy2ed's risk class 7 to 9, renaming batch9's test from test_real_store_reflects_batch8_corpus_growth to test_real_store_reflects_batch9_corpus_growth to match its own prose's real numbering, and keeping both regression tests. Recomputed live after the merge via scripts/segmenter_governance_status.py: document_count=117, val_ceiling/test_ceiling=18/18 (higher than either round's own pre-merge number, confirming the RFC 0012 assign_splits ratio math is nonlinear -- naive addition would have under-stated it). test_segmenter_audit_scripts.py auto-merged cleanly (batch9's new allowlist entry, no overlap with this round's changes)."
---

# Evidencia: conflito de merge resolvido, numeros recalculados ao vivo

`uv run okf-parser check` e `uv run python scripts/check_agent_run_completeness.py knowledge/agent-runs`
seguem limpos apos a mescla (bundle inclui agora tambem o relatorio
`AgentRun` completo da rodada hv2ep2, trazido pelo merge).
