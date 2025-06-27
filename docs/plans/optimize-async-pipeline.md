# Optimize Async Pipeline (`async_diario_pipeline.py`)

## Problem Statement
- **What problem does this solve?**
  The `async_diario_pipeline.py` is responsible for processing a large number of diários (5,058 historical items mentioned in `AGENTS.md`). While it's designed for concurrency, there might be bottlenecks, suboptimal resource utilization, or areas where performance can be further enhanced to process diários faster and more efficiently.
- **Why is this important?**
  Efficient pipeline processing is crucial for handling large backlogs of historical data and for timely processing of new diários. Optimizations can lead to reduced processing times, lower resource consumption (CPU, memory, network), and potentially lower operational costs if running in cloud environments.
- **Current limitations**
  - Default concurrency limits (3 downloads, 2 uploads) might not be optimal for all environments or tasks.
  - Potential I/O bottlenecks when reading/writing files or interacting with the database.
  - Suboptimal task scheduling or resource sharing in asyncio event loop.
  - Lack of detailed performance profiling to identify specific bottlenecks.
  - Error handling within concurrent tasks might lead to inefficiencies if not managed carefully.

## Proposed Solution
- **High-level approach**
  Systematically analyze the performance of `async_diario_pipeline.py`, identify bottlenecks, and implement optimizations. This includes tuning concurrency parameters, improving I/O operations, optimizing asyncio usage, and potentially refactoring critical sections of the code for better performance.
- **Technical architecture**
  1.  **Performance Profiling**:
      - Utilize Python's `cProfile` and `pstats` for CPU-bound bottlenecks.
      - Use `asyncio` debugging tools and potentially `uvloop` (as an alternative event loop) for I/O-bound and event loop performance analysis.
      - Add fine-grained timing (e.g., `time.perf_counter()`) around key operations within the pipeline stages.
  2.  **Concurrency Tuning**:
      - Make concurrency limits (e.g., for downloads, uploads, LLM calls) more dynamically configurable, perhaps based on available system resources or user settings.
      - Explore using `asyncio.Semaphore` more extensively to control access to shared resources or rate-limit specific operations.
  3.  **I/O Optimization**:
      - For database interactions, ensure connections are managed efficiently in an async context (e.g., using an async-compatible DB driver or connection pool if DuckDB supports it, or offloading DB writes to a separate thread pool). Current `CausaGanhaDB` seems synchronous.
      - Optimize file I/O operations (e.g., reading/writing PDFs, JSON files) by using async file libraries if beneficial, or by ensuring blocking file I/O is run in thread pool executors to not block the event loop.
  4.  **Asyncio Best Practices**:
      - Review `await` usage to ensure it's not blocking the event loop unnecessarily.
      - Optimize task creation and management (e.g., using `asyncio.gather` effectively).
      - Ensure proper exception handling in async tasks to prevent silent failures or resource leaks.
  5.  **Batching**:
      - Where feasible, batch operations (e.g., database updates, IA metadata updates) to reduce overhead.
  6.  **Resource Management**:
      - Monitor memory usage during pipeline runs and identify potential memory leaks or areas for optimization.
      - Ensure resources like file handles and network connections are properly released.

- **Implementation steps**
  1.  **Phase 1: Profiling and Bottleneck Identification (Week 1)**
      - Set up a benchmark scenario using a representative subset of diários.
      - Profile the `async_diario_pipeline.py` under this benchmark to identify CPU, I/O, and event loop bottlenecks.
      - Analyze logs and existing metrics (`--stats-only` output) for performance insights.
  2.  **Phase 2: Low-Hanging Fruit & Concurrency Tuning (Weeks 2-3)**
      - Implement more flexible configuration for concurrency parameters.
      - Address any obvious bottlenecks identified in Phase 1 (e.g., inefficient loops, synchronous calls blocking the event loop).
      - Experiment with different semaphore limits for downloads, uploads, and LLM calls to find optimal defaults or guidance.
  3.  **Phase 3: I/O and Database Optimization (Weeks 4-5)**
      - Investigate options for making database interactions more async-friendly. This might involve wrapping synchronous DuckDB calls in `loop.run_in_executor` or exploring async drivers if they become available.
      - Optimize file operations, especially for large numbers of small files or large PDF processing.
  4.  **Phase 4: Advanced Async Optimizations & Testing (Week 6)**
      - Review and optimize asyncio task management and exception handling within concurrent tasks.
      - Consider replacing the default event loop with `uvloop` and measure performance impact.
      - Re-run benchmarks to quantify performance improvements.
      - Ensure no regressions in functionality due to optimizations.
  5.  **Phase 5: Documentation (Ongoing)**
      - Document performance findings, applied optimizations, and recommendations for configuring concurrency.

## Success Criteria
- **Reduced Processing Time**: Significant reduction (e.g., 20-30% or more) in the total time taken to process a benchmark set of diários.
- **Improved Resource Utilization**: More balanced CPU, memory, and network usage during pipeline execution. Reduced idle times.
- **Scalability**: The pipeline can handle larger volumes of diários more effectively with tuned concurrency.
- **Stability**: Optimizations do not introduce new instabilities or errors.
- **Measurable Improvements**: Clear metrics (e.g., diários processed per minute, average time per stage) show tangible performance gains.
- **Configurability**: Users or system administrators can tune key performance parameters.

## Implementation Plan (High-Level for this document)
1.  **Profile & Analyze**: Benchmark current `async_diario_pipeline.py`, identify bottlenecks using profiling tools.
2.  **Tune Concurrency**: Make download/upload/LLM concurrency limits configurable. Experiment with `asyncio.Semaphore` values.
3.  **Optimize I/O**: Focus on database interactions (async wrappers for DuckDB) and file handling within the async context.
4.  **Refine Async Patterns**: Review `await` usage, task management, and exception handling in async code. Test `uvloop`.
5.  **Benchmark & Document**: Measure improvements against baseline. Document findings and configuration advice.

## Risks & Mitigations
- **Risk 1: Premature Optimization**: Spending time optimizing non-bottlenecked code.
  - *Mitigation*: Rely heavily on profiling data (Phase 1) to guide optimization efforts. Focus on the most impactful areas first.
- **Risk 2: Increased Complexity**: Some performance optimizations can make code harder to understand or maintain.
  - *Mitigation*: Prioritize clear and maintainable optimizations. Document complex optimizations thoroughly. Balance performance gains against complexity costs.
- **Risk 3: Introducing Race Conditions or Deadlocks**: Incorrectly managing concurrency or shared resources can lead to new bugs.
  - *Mitigation*: Use asyncio synchronization primitives (Semaphore, Lock) correctly. Conduct thorough testing under concurrent load. Code reviews by developers experienced with asyncio.
- **Risk 4: External System Limits**: Optimizations might hit rate limits or bottlenecks in external systems (TJRO website, IA, Gemini API) more quickly.
  - *Mitigation*: Ensure that interactions with external systems respect their rate limits. The existing built-in exponential backoff is good. Optimizations should focus on internal efficiency, allowing the system to make better use of the allowed quota from external services.
- **Risk 5: Diminishing Returns**: After initial optimizations, further gains may require disproportionate effort.
  - *Mitigation*: Set realistic performance goals. Stop optimizing when the effort outweighs the benefits or when performance is "good enough" for the project's needs.

## Dependencies
- Python `asyncio`, `cProfile`, `pstats`.
- Potentially `uvloop`.
- Existing libraries like `aiohttp`.
- Benchmarking tools or scripts.
