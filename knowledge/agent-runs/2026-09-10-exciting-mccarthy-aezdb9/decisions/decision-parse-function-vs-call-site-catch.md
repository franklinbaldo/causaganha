---
type: AgentDecision
id: "2026-09-10-exciting-mccarthy-aezdb9-decision-parse-function-vs-call-site-catch"
run_id: "2026-09-10-exciting-mccarthy-aezdb9"
goal_id: "2026-09-10-exciting-mccarthy-aezdb9-goal-ia-rate-limit-fallback"
question: "Fix by validating the env var at parse time (reject <=0, fall back to default before AsyncLimiter is ever constructed), or by wrapping the _IA_RATE_LIMITER.acquire() call site in upload_zip with a try/except ValueError?"
choice: "Extract a pure `_parse_ia_max_rate(raw: str | None, default: int = 4) -> int` function and call it once at module import time, in place of the previous bare try/except. Reject the fix-at-call-site approach."
rationale: "A call-site try/except around acquire() would have to run on every single upload (a hot path) purely to guard against a misconfiguration that is constant for the process's whole lifetime -- and CLAUDE.md's own rule against blind `except Exception` pushes toward a narrow `except ValueError`, which is fragile because AsyncLimiter could plausibly raise ValueError for an unrelated reason (e.g. a future call site passing a bad `amount`) and that would then be silently swallowed as 'bad rate limit config' too. Parsing validation is also strictly cheaper: it runs once at import time instead of per-upload, and it keeps the invariant 'the module-level _IA_RATE_LIMITER, once constructed, always has a usable max_rate' local to the one place that constructs it, rather than pushing the burden of defending against a broken limiter onto every caller down the chain. Extracting the parsing into its own function (rather than fixing it inline in the try/except) was necessary anyway for testability: the module-level assignment runs once at import time from the real environment, so a bare inline fix could not be exercised by a test without reload-the-module gymnastics -- a pure function with an explicit `raw` parameter is directly unit-testable and mirrors the existing test style in this package (small, focused pure-function tests, e.g. tests/djen_backup/test_retry.py)."
---

# Decisão: validar no parse, não capturar no ponto de chamada

Extrair `_parse_ia_max_rate` e chamá-la uma vez na importação do módulo evita reintroduzir a checagem em todo `upload_zip`, mantém a invariante "o limiter, uma vez construído, é sempre utilizável" e viabiliza teste unitário direto sem recarregar o módulo.
