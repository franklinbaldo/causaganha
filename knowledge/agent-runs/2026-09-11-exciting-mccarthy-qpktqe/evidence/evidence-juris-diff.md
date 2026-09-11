---
type: AgentEvidence
id: "2026-09-11-exciting-mccarthy-qpktqe-evidence-juris-diff"
run_id: "2026-09-11-exciting-mccarthy-qpktqe"
goal_id: "2026-09-11-exciting-mccarthy-qpktqe-goal-juris-url-percent-encoding-mismatch"
kind: "diff"
reference: "scripts/reconcile_processos.py (+10/-1), tests/test_reconcile_processos.py (+38/-0)"
summary: "reconcile_processos.py: imports urllib.parse.quote; fetch_juris_from_ia's docstring gains a paragraph explaining the percent-encoding requirement and why a mismatch would break CNJ-scoped JURIS search; the URL construction line changes from `url = f\"{_IA_BASE}/{item}/{name}\"` to `url = f\"{_IA_BASE}/{item}/{quote(name)}\"` (the local cache path and print label still use the raw `name`, unaffected). test_reconcile_processos.py: imports causaganha.decisoes.published; adds test_fetch_juris_from_ia_matches_published_juris_url_encoding, which mocks a JURIS IA item with a real diacritic filename and cross-checks fetch_juris_from_ia's stored URL against published.discover_published_juris_datasets's independently-computed URL for the same (tipo, mes_ano)."
---

# Diff

```diff
+from urllib.parse import quote
...
             for name in wanted:
-                url = f"{_IA_BASE}/{item}/{name}"
+                url = f"{_IA_BASE}/{item}/{quote(name)}"
                 path = _fetch_cached(client, url, cache / item / name, f"JURIS {item}/{name}")
                 paths.append(path)
                 urls[path] = url
```

`scripts/reconcile_processos.py` (+10/-1), `tests/test_reconcile_processos.py` (+38/-0, novo teste de regressão cruzando `fetch_juris_from_ia` com `published.discover_published_juris_datasets`).
