---
goal: "Corrigir request_with_retry (src/djen_backup/retry.py) para que o retry baseado em resultado (retry_if_result: 408/429/500/502/503/504 e 400/404 condicionais) realmente reexecute a requisição, e cobrir com testes."
id: "run-goals/20260907t143126z-fa-a-o-melhor-avan-o-poss-vel-n/goal-fix-retry-result-predicate"
kind: "task-advance"
rationale: "Auditoria de src/djen_backup/retry.py (módulo sem nenhum teste direto) revelou que o idiom 'async for attempt in AsyncRetrying(...): with attempt: return await ...' faz o 'return' escapar da função inteira no primeiro resultado, contornando silenciosamente qualquer predicado retry_if_result — só exceptions (httpx.TransportError/TimeoutException) de fato disparavam retry. Isso é usado por todo o motor de sync (checkers, downloaders, uploaders via djen.py e archive.py), então uma resposta 503/429/500 transitória da DJEN ou da IA nunca era reexecutada dentro da mesma chamada, apesar do código e da política documentada dizerem o contrário."
run: "runs/20260907T143126Z-fa-a-o-melhor-avan-o-poss-vel-neste-reposit-rio"
status: "achieved"
success_signal: "tests/djen_backup/test_retry.py RED confirmado contra a implementação antiga (4 testes falhando: retry em 503 não reexecuta, exhaustion não devolve a última resposta, 400/404 condicionais não reexecutam); GREEN após reescrever request_with_retry para usar a forma chamável 'await retryer(client.request, ...)' e capturar tenacity.RetryError para devolver a última resposta; suíte completa (uv run pytest -q) permanece 100% verde (652 testes, 10 novos) e ruff check/format limpos."
type: "RunGoal"
---

# RunGoal
