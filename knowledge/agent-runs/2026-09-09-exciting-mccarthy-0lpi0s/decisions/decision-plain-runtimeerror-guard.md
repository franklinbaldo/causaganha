---
type: AgentDecision
id: "2026-09-09-exciting-mccarthy-0lpi0s-decision-plain-runtimeerror-guard"
run_id: "2026-09-09-exciting-mccarthy-0lpi0s"
goal_id: "2026-09-09-exciting-mccarthy-0lpi0s-goal-fixture-network-guard"
question: "Should the fixture's network guard raise OSError/httpx.HTTPError (the exception types real network failures already produce) or something else, when it intercepts a blocked urllib.request.urlopen/httpx.Client.send call?"
choice: "Raise a new, plain RuntimeError subclass (RealNetworkAccessError), not OSError or httpx.HTTPError."
rationale: "render_queries.py's _try_download_parquet() already catches OSError around its urlopen call and degrades to a silent 'WARNING: could not download' + returns None (an optional contract then just gets skipped); reconcile_processos.py's ensure_juris_parquets()/ensure_datajud_parquets() already catch (httpx.HTTPError, OSError, SourceDataError) and degrade similarly. If the guard raised either of those types, both existing handlers would swallow it exactly like a real network failure, defeating the goal (a loud, immediate, clearly-diagnosed crash for 'a source's fixture isolation is missing' -- a bug in the fixture, not a legitimate absent-data case). A plain RuntimeError subclass propagates past both handlers uncaught, and further propagates uncaught out of render_all() itself, since render_all()'s per-spec loop (scripts/render_queries.py ~line 894-896) calls spec.register(con) with no try/except at all -- only the later run_query() SQL-execution step is guarded, against duckdb.CatalogException specifically."
---

# Decisão: exceção própria, não OSError/httpx.HTTPError

A guarda de rede levanta `RealNetworkAccessError(RuntimeError)`, deliberadamente não uma subclasse de `OSError` nem de `httpx.HTTPError` -- ambos já são capturados e degradados silenciosamente em pontos existentes do código (`_try_download_parquet`, `ensure_juris_parquets`/`ensure_datajud_parquets`). Uma exceção própria atravessa esses handlers sem ser engolida e propaga sem tratamento até fora de `render_all()`, que não envolve `spec.register(con)` em try/except algum.
