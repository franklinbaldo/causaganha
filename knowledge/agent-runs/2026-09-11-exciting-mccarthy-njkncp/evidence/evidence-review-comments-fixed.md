---
type: AgentEvidence
id: "2026-09-11-exciting-mccarthy-njkncp-evidence-review-comments-fixed"
run_id: "2026-09-11-exciting-mccarthy-njkncp"
goal_id: "2026-09-11-exciting-mccarthy-njkncp-goal-cobertura-malformed-report"
kind: "review"
reference: "PR #1454 Codex automated Code Review (2 review comments on src/causaganha/processos/service.py:226 and :247)"
summary: "Codex's Code Review on PR #1454 found two real P2 bugs in this round's own fix, both verified and fixed: (1) `isinstance(registros, int)` accepts `bool` (a Python int subclass), so `\"rows\": true` survived as `registros=True`, which the public Pydantic contract would coerce to a fabricated count of 1 -- fixed by also excluding `isinstance(registros, bool)`. (2) a present-but-non-dict `sources` value (null/array/string) was silently treated as an empty mapping, returning a *successful* empty coverage list indistinguishable from a report that genuinely lists zero sources -- fixed by returning None (the same 'relatório indisponível' path as a missing file) when `sources` is present but not a dict, while a genuinely absent `sources` key still defaults to an empty mapping (backward compatible, no existing test exercises that case as unavailable). Two new regression tests added (test_report_rejects_boolean_rows_instead_of_counting_as_one, test_report_with_non_object_sources_is_unavailable_not_empty), both confirmed RED against the pre-review-fix code and GREEN after. A third Codex comment (on knowledge/agent-runs/.../run.md, arguing this legacy AgentRun bundle should not exist because knowledge/agent-runs/index.md and .claude/hourly-loop.md describe a migration to Wisk) was read and NOT acted on: this session's own scheduled-task prompt explicitly instructs creating this exact AgentRun scaffold for this routine, and 7 consecutive same-lineage rounds today (r3erpr through this one) have used it successfully -- already reasoned through and recorded in this round's own reading-okf.md as 'no real conflict, distinct routine from the hourly loop.'"
---

# Review: dois bugs P2 reais corrigidos, um comentário não endereçado (com justificativa)

Codex encontrou dois bugs reais na correção desta rodada (booleans em `rows`, `sources` não-dict tratado como vazio-com-sucesso) — ambos corrigidos com testes RED→GREEN. O terceiro comentário (sobre o bundle `AgentRun`) foi avaliado e não endereçado: contradiz a própria instrução desta rotina agendada, já documentada em `reading-okf.md`.
