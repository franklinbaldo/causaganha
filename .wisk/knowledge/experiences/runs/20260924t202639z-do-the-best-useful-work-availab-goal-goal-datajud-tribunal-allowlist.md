---
goal: "Fix issue #1615: validate 'tribunal' against a canonical allowlist in all three DataJud MCP tools (datajud_status, datajud_facetas, processo_estado) before it reaches any network request, IA item id or bundle filename."
id: "run-goals/20260924t202639z-do-the-best-useful-work-availab/goal-datajud-tribunal-allowlist"
kind: "task-advance"
rationale: "tribunal is currently interpolated unvalidated (only .lower()'d) into DataJud's search endpoint path and Internet Archive item id/bundle filename -- a caller-supplied value like '../tjro' reaches an unexpected upstream path segment, exactly the egress/identity-confusion threat issue #1615 describes. Chosen from a live GitHub survey (this round's evidence-credential-and-work-survey) as the best-scoped, self-contained, TDD-shaped work available with issue #1471 blocked and no PR in flight for #1615."
run: "runs/20260924T202639Z-do-the-best-useful-work-available-in-this-reposi"
status: "achieved"
success_signal: "A new datajud.tribunais.validar_tribunal() gate exists; each of the three tools calls it before touching network/service layers; a live RED test proves the injection is real (respx/monkeypatch caught the malicious request/download attempt before the fix) and turns GREEN after; full pytest suite and ruff stay green."
type: "RunGoal"
---

# RunGoal
