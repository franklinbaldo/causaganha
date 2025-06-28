# Queue-based Job Orchestrator

## Problem Statement
- **What problem does this solve?**
  The current `async_diario_pipeline.py` processes download tasks using a simple `asyncio.Semaphore` to limit concurrency. As the project scales to thousands of diarios and additional tribunals, we need a more flexible mechanism to manage download jobs, retry logic and prioritization.
- **Why is this important?**
  A queue orchestrator decouples job production from consumption, enabling better resource utilization, dynamic concurrency tuning and potential future integrations with external job queues.

## Proposed Solution
- Introduce a `DownloadOrchestrator` class using `asyncio.Queue`.
- Populate the queue with diario metadata and spawn a configurable number of worker tasks.
- Each worker will invoke `AsyncDiarioPipeline.process_diario` allowing existing download and upload logic to remain largely unchanged.
- The orchestrator will track results and expose simple statistics for benchmarking.

## Implementation Steps
1. Create `src/download_orchestrator.py` with `DownloadOrchestrator` class.
2. Update `async_diario_pipeline.py` to optionally run through the orchestrator when `use_queue=True`.
3. Add unit test verifying that the orchestrator processes items with the desired concurrency.
4. Document the new component in `docs/diagrams/async_pipeline.mermaid` and reference it in architecture docs.

## Success Criteria
- Pipeline can process a list of diarios using the orchestrator without regression.
- Concurrency level is respected and configurable.
- Benchmark tests can measure throughput via orchestrator statistics.

