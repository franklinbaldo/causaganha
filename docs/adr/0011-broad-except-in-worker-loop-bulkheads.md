# 11. Broad `except Exception` is accepted at per-item worker-loop bulkheads

Date: 2026-09-08

## Status

Accepted

## Context

CLAUDE.md states flatly: "No blind `except Exception`. Use specific types:
`httpx.HTTPError`, `httpx.RequestError`, `OSError`, `RuntimeError`." In
practice four call sites violate that rule as written, and have for
multiple prior agent rounds without being fixed, because each round found
the same blocker: deciding what to do here is a policy call, not a
mechanical fix, so it kept getting logged as a lead and carried to the next
round instead of resolved.

The four sites:

- `src/djen_backup/archive.py:264` — wraps `ia_s3.upload_to_ia()` inside the
  per-item upload lock, one item at a time, inside the uploader worker
  pool's loop over the whole backlog.
- `src/causaganha/analysis/llm_analyzer.py:387` and `:499` — wrap a single
  `litellm.acompletion()` call inside a loop over configured fallback
  models (and, in the batch variant, API keys), one call at a time.
- `src/causaganha/consolidate/cli.py:160` — wraps exporting one table
  inside a loop over `TABLES`, one table at a time.

All four share one shape: a loop processes N independent units of work
(an upload, an LLM call, a table export), and the `except Exception` sits
around exactly one iteration's unit of work, not around the loop itself or
around unrelated logic. All four immediately call `log.exception(...)` /
`logger.exception(...)` — which captures the full traceback for postmortem
— before deciding what to do next: return a failure sentinel and let the
caller's own retry/reconciliation loop (the manifest, the circuit breaker,
`stats["export_failures"]`) pick it up later, or re-raise when the error is
classified as non-retryable (both LLM sites already do this; see
`_is_retryable`).

Ruff's BLE001 (flake8-blind-except) does not flag any of these four sites,
because `.exception(...)` in the handler satisfies the rule's own
logging-was-preserved exemption — confirmed directly: `logger.exception(...)`
suppresses BLE001, `logger.warning(...)` does not. So the sites are
lint-clean today; the actual gap is that CLAUDE.md's prose is stricter than
what the codebase (and ruff's own configured rule) actually enforces, and
narrower than what these four sites' architecture needs.

**Why narrowing to specific types is the wrong fix here**, unlike a typical
one-off `except Exception`:

- `archive.py:264`'s `ia_s3.upload_to_ia()` already catches its own known
  failure modes internally (`httpx.HTTPError`, `httpx.RequestError`,
  `OSError`) and returns `False` — anything that still escapes to the
  caller is by definition not one of those known cases, i.e. a bug in the
  metadata/header-building code that runs before `upload_to_ia`'s own
  `try`. Narrowing the caller's catch would let that bug propagate out of
  the uploader worker pool's loop entirely, killing the whole pool instead
  of failing just the one item — worse for a system whose whole point
  (CLAUDE.md: "Periodic IA upload every 10 min protects against crashes")
  is resilience against exactly this kind of per-item failure.
- `llm_analyzer.py`'s two sites call `litellm.acompletion()`, which
  multiplexes over multiple upstream provider SDKs (OpenAI, Gemini,
  Anthropic, Bedrock, ...). `litellm.exceptions.APIError` is the common
  base for provider/network failures, but litellm's own guardrail/budget
  exceptions (`BudgetExceededError`, `GuardrailRaisedException`,
  `BlockedPiiEntityError`, `SensitiveDataRouteException`,
  `ModifyResponseException`) inherit directly from `Exception`, not from
  `APIError` — confirmed by inspecting `litellm.exceptions`'s class MROs.
  Narrowing to `APIError` would silently stop retrying/falling-back on
  those, changing behavior for cases this code has no evidence it should
  special-case. The existing `_is_retryable()` already does the real
  discrimination by message content across whatever exception type comes
  back, and both sites already re-raise anything classified as
  non-retryable (`else: logger.exception(...); raise`) — so nothing here
  is silently swallowed.
- `cli.py:160`'s `export_table_sync` runs arbitrary ibis/DuckDB/PyArrow
  export code per table via `asyncio.to_thread`; the failure surface
  spans multiple libraries with no single common ancestor exception
  narrower than `Exception`, and a failure in one table must not abort
  exporting the rest (the loop already tracks `stats["export_failures"]`
  precisely so partial failures stay visible and countable).

This is the standard "bulkhead" pattern for resilient batch/worker
systems (isolate each unit of work so one failure can't take down the
whole batch), not carelessness — but it needs to be a documented decision
so ruff's silent exemption and CLAUDE.md's stricter prose stop disagreeing,
and so a future contributor doesn't "fix" it by turning one item's bug into
a whole-pool crash.

## Decision

1. **Keep `except Exception` at all four sites.** Each already satisfies
   the two conditions that make a broad catch acceptable at a bulkhead
   boundary: (a) it wraps exactly one independent unit of work inside a
   loop over many, not unrelated surrounding logic; (b) the full exception
   is logged via `log.exception()`/`logger.exception()` before the handler
   decides to record-and-continue or re-raise — nothing is swallowed
   silently.
2. **Add a one-line comment at each site** pointing to this ADR, so the
   intent reads locally instead of requiring the reader to already know
   the policy.
3. **Amend CLAUDE.md's "No blind `except Exception`" rule** to state the
   real, narrower policy: specific types at request/parse boundaries
   (unchanged default), *except* at a per-item bulkhead inside a
   worker-pool loop over independent units of work, where a broad catch
   paired with `.exception()` logging is accepted and must cite this ADR.
4. **Do not change ruff.toml.** BLE001 already exempts a handler that logs
   via `.exception(...)`, which is exactly the invariant this decision
   requires; no per-file or per-line ignore is needed at any of the four
   sites.

## Consequences

- **Positive**: closes a lead that had been carried across at least three
  prior agent rounds as "needs a human decision" without ever being
  decided — the decision is now written down, and CLAUDE.md no longer
  contradicts what the codebase (and ruff's own configured rule) already
  does.
- **Positive**: a future `except Exception` elsewhere in the codebase is
  now checked against a concrete, written test (per-item bulkhead + full
  traceback logging) instead of an all-or-nothing prose ban that the
  codebase was already quietly not following.
- **Negative**: a genuine, unanticipated bug at one of these four sites
  will still be recorded as a per-item failure (logged, counted, retried
  later) rather than crashing loudly at the point of the bug. This is the
  accepted trade-off of the bulkhead pattern for a long-running pipeline
  processing thousands of independent items; it is mitigated by
  `log.exception()`'s full traceback making the bug discoverable in logs
  even though it doesn't halt the process.
