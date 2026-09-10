---
type: AgentDecision
id: "2026-09-10-exciting-mccarthy-r3erpr-decision-reorder-guards"
run_id: "2026-09-10-exciting-mccarthy-r3erpr"
goal_id: "2026-09-10-exciting-mccarthy-r3erpr-goal-cb-probe-lock-order"
question: "Fix by reordering upload_zip's two guards (lock check before circuit_breaker.allow_request()), by adding a way for the caller to 'return' an unused probe to CircuitBreaker, or by having upload_zip call record_failure() on ItemBusyError to at least resolve the probe's state?"
choice: "Keep the single upload_zip body. Move the `try_lock and lock.locked()` check (raise ItemBusyError) to run before `circuit_breaker.allow_request()`, instead of after."
rationale: "Rejected adding a release_probe()-style method to CircuitBreaker: adds a new public method and a third state-transition path for a problem the reorder solves for free -- more surface area for the same outcome. Rejected calling record_failure() on ItemBusyError: that would count a lock conflict as an IA failure, which is semantically wrong (per CLAUDE.md, ItemBusyError is a re-queue signal, not a failure signal) and would make the breaker over-eager to open on high lock contention that has nothing to do with IA's health. Chose the reorder: the lock check has zero side effects and doesn't need the circuit breaker's involvement at all, so checking it first means a busy item never touches the breaker -- the probe stays available for the next caller, whether that's the same worker retrying a different item or another worker. This also matches the existing precedent of ordering fast, side-effect-free checks before expensive/stateful ones."
---

# Decisão: reordenar os dois guardas em vez de mudar o contrato do CircuitBreaker

Verificar o lock por item antes de chamar `circuit_breaker.allow_request()` resolve o desperdício do probe sem adicionar estado novo ao `CircuitBreaker` nem tratar contenção de lock como falha de IA.
