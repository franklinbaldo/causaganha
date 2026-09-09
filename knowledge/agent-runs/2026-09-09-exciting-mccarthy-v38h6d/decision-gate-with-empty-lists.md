---
type: AgentDecision
id: "2026-09-09-exciting-mccarthy-v38h6d-decision-gate-with-empty-lists"
run_id: "2026-09-09-exciting-mccarthy-v38h6d"
goal_id: "2026-09-09-exciting-mccarthy-v38h6d-goal-check-only-no-io"
question: "Gate check_only by making feeder_task/dl_tasks/upload_tasks empty/None (so the existing None-termination and gather() loops naturally no-op), or restructure run_pipeline with an early-return / separate check-only code path?"
choice: "Keep the single unified run_pipeline body. Make backlog `[]` and feeder_task/dl_tasks/upload_tasks `None`/`[]` when check_only, guard the one `await asyncio.gather(feeder_task, ...)` call with `if feeder_task is not None`, and leave every downstream line (the `for _ in dl_tasks: await _put_with_deadline(download_queue, None)`, `await asyncio.gather(*dl_tasks, ...)`, the same pair for upload_tasks, `upload_queue.join()`) completely untouched."
rationale: "The downstream loops already iterate over dl_tasks/upload_tasks to push sentinel Nones and gather results -- an empty list makes every one of those loops and gather() calls a correct, already-existing no-op with zero new branching. upload_queue.join() on an empty, never-fed queue returns immediately (0 unfinished tasks), so no new timeout/short-circuit logic was needed there either. A separate check-only code path (e.g. returning right after the checker phase) would have to re-implement the deadline_monitor cleanup, circuit_breaker logging, and the try/finally shutdown block that the unified path already handles correctly -- pure duplication for behavior the empty-list approach gets for free. This keeps the diff to the minimum needed to make check_only's documented contract true: 4 conditional expressions plus a null guard, no restructuring of the pipeline's control flow or its worker-shutdown protocol."
---

# Decisao: sentinela de lista vazia, nao um segundo fluxo de codigo

Optei por deixar `feeder_task`/`dl_tasks`/`upload_tasks` vazios (`None`/`[]`) quando `check_only=True`, em vez de bifurcar `run_pipeline` num segundo caminho de codigo dedicado a "check only". Os loops de encerramento (`for _ in dl_tasks: ...`, `gather(*dl_tasks)`, `upload_queue.join()`) ja tratam listas vazias como no-op corretamente -- reaproveitar essa estrutura evita duplicar a logica de shutdown (deadline_monitor, circuit_breaker, try/finally) que um segundo fluxo teria que reimplementar.
