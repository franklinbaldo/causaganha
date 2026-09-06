---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-sk8ec6-decision-classification-boundary"
run_id: "2026-09-06-exciting-mccarthy-sk8ec6"
goal_id: "2026-09-06-exciting-mccarthy-sk8ec6-goal-fix-1193-dataset-availability"
question: "Exactly where is the missing/unavailable boundary drawn? In particular: does 'valid metadata response but zero Parquet files' count as confirmed absence (missing) or as an unclear/unavailable case?"
choice: "missing = HTTP 404, or a well-formed 2xx metadata response whose file list contains no .parquet entries. unavailable = a rejected fetch (network failure), any other non-2xx status (5xx and any other non-404 non-ok status), or a 2xx response whose body cannot be parsed as JSON / does not have the expected shape. Only 'missing' results are cached in datasetCache; 'unavailable' results are never cached, so the effect re-probes on any dependency change and an explicit retry button lets the user force a fresh probe without changing the selection."
rationale: "#1193's own 'Proposta' section states verbatim: 'reservar missing apenas para evidência de ausência real do item/Parquet (por exemplo, resposta 404 ou metadata válida sem Parquet esperado)' — explicitly grouping 'no Parquet in a valid response' with 404 as confirmed absence, not as an error state. Everything else (network failure, 5xx, malformed body) is, by construction, a failure to observe the dataset's true state rather than evidence about it, so it must not be recorded as if it were. Not caching 'unavailable' avoids freezing a transient failure as permanent for the rest of the session (acceptance criterion: 'erro transitório não fica cacheado como ausência permanente durante a sessão') while still caching confirmed 'missing' verdicts, preserving the original design's intent of not re-probing datasets already proven absent."
---

# Decisão: fronteira exata entre `missing` e `unavailable`

`missing` = 404 OU resposta 2xx válida sem nenhum arquivo `.parquet` (conforme o texto literal da proposta da `#1193`, que agrupa esses dois casos como evidência real de ausência). `unavailable` = falha de rede, qualquer outro status não-OK, ou corpo de resposta inválido/inesperado — nunca cacheado, para permitir retry sem congelar o erro transitório como ausência permanente.
