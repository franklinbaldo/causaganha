# Enhance Internet Archive (IA) Interaction Robustness

## Problem Statement
- **What problem does this solve?**
  The CausaGanha system relies heavily on Internet Archive for storing diário PDFs and for synchronizing the shared DuckDB database. Interactions with external services like IA can be prone to transient errors, rate limits, or inconsistencies. The current IA interaction logic (in `ia_helpers.py`, `ia_database_sync.py`, and CLI commands) might need enhancements to handle these issues more gracefully and reliably.
- **Why is this important?**
  Robust IA interaction is critical for data integrity, pipeline reliability, and the effectiveness of the distributed database system. Failures in IA operations can lead to data loss, pipeline stalls, or database desynchronization.
- **Current limitations**
  - Error handling for `ia` CLI tool subprocess calls might be basic.
  - Retry mechanisms for IA operations might be absent or simplistic.
  - The current lock system for database synchronization (`ia_database_sync.py`) is sentinel file-based and might have limitations or race conditions in highly concurrent scenarios (though current GitHub Actions workflows might mitigate this).
  - Detection and handling of IA-specific issues (e.g., item not yet live after upload, metadata update delays) could be improved.

## Proposed Solution
- **High-level approach**
  Improve the robustness of all IA interactions by implementing comprehensive error handling, retry mechanisms, and potentially refining the database synchronization locking mechanism. This involves enhancing `ia_helpers.py` and `ia_database_sync.py`.
- **Technical architecture**
  1.  **Resilient `ia` CLI Wrapper**:
      - Enhance `execute_ia_command_async` in `ia_helpers.py`.
      - Implement retries with exponential backoff and jitter for `ia` CLI commands that are known to be flaky or rate-limited.
      - Parse `ia` CLI output more thoroughly to detect specific errors or success conditions.
      - Raise custom `IAError` exceptions with detailed context.
  2.  **Upload/Download Stability**:
      - For PDF uploads to IA (within `archive_diario_to_master_item` or similar):
          - Verify upload success, potentially by trying to fetch metadata or the file itself shortly after upload (with retries, as IA can have delays).
      - For downloads from IA (e.g., in `analyze` stage or `ia_database_sync.py`):
          - Use the refactored `DownloaderService` (from "Refactor Downloader Module" plan) if it's suitable for IA downloads, or ensure similar resilience is built into IA-specific download logic.
  3.  **Database Sync Locking Mechanism Review**:
      - Analyze the current sentinel lock file mechanism in `ia_database_sync.py`.
      - **Option A (Simpler):** Enhance current lock:
          - Add lock acquisition timeouts.
          - Ensure atomic lock creation/deletion if possible with `ia` CLI.
          - Improve logging around lock acquisition/release.
      - **Option B (More Complex, if needed):** Explore alternative distributed lock primitives if IA offers them or if a more robust external service could be minimally used (though this adds complexity). For now, enhancing the current system is preferred.
      - Consider adding a "force unlock" or "stale lock cleanup" mechanism for manual intervention if locks get stuck.
  4.  **IA Item Health Checks**:
      - Implement functions to check the status of the master IA item or specific files within it (e.g., `is_file_accessible_on_ia(item_id, remote_path)`).
  5.  **Configuration**:
      - Make IA interaction parameters (retries, timeouts) configurable in `config.toml`.

- **Implementation steps**
  1.  **Phase 1: Resilient `ia` CLI Wrapper (Weeks 1-2)**
      - Refactor `ia_helpers.py` to add robust retry logic (e.g., using `tenacity`) to `execute_ia_command_async`.
      - Improve error parsing from `ia` CLI output.
      - Introduce specific `IAError` subtypes (e.g., `IAUploadError`, `IADownloadError`, `IALockError`).
  2.  **Phase 2: Upload/Download Verification (Weeks 3-4)**
      - Implement post-upload verification checks for diário PDFs.
      - Ensure downloads from IA (for analysis or DB sync) are resilient, using the improved wrapper or `DownloaderService`.
  3.  **Phase 3: Database Lock Enhancement (Weeks 5-6)**
      - Review and enhance the existing sentinel lock file mechanism in `ia_database_sync.py`:
          - Add configurable timeouts for lock acquisition.
          - Improve logging for lock operations.
          - Develop a procedure or script for identifying and potentially clearing stale locks (with safeguards).
  4.  **Phase 4: Testing and Documentation (Week 7)**
      - Write integration tests for IA interactions, mocking `subprocess` calls to `ia` CLI to simulate various success/failure scenarios and retries.
      - Test the database sync locking under simulated concurrent access if possible (this is hard to test perfectly without real concurrency).
      - Document the IA interaction strategy, error handling, and troubleshooting for IA-related issues.

## Success Criteria
- **Increased Reliability**: IA operations (upload, download, sync) succeed more often despite transient IA issues or network glitches.
- **Graceful Failure**: When IA operations genuinely fail after retries, the system logs detailed errors and fails gracefully without crashing or leaving inconsistent state where possible.
- **Improved Database Sync**: The shared database synchronization is more robust, with fewer chances of conflicts or stale locks.
- **Better Diagnostics**: Logs provide clear information about IA interaction attempts, errors, and retries.
- **Maintainability**: IA interaction logic is well-organized, configurable, and easier to debug.
- **No Data Loss**: Robust interactions prevent loss of diários during upload or corruption of the shared database during sync.

## Implementation Plan (High-Level for this document)
1.  **Resilient `ia` Wrapper**: Enhance `ia_helpers.py` with retries (`tenacity`) and better error parsing for `ia` CLI calls.
2.  **Stable Uploads/Downloads**: Add post-upload verification. Ensure resilient IA downloads.
3.  **Improve DB Sync Lock**: Enhance `ia_database_sync.py` lock mechanism with timeouts and better logging. Develop stale lock handling.
4.  **Test & Document**: Write integration tests mocking `ia` CLI. Document IA interaction strategy.

## Risks & Mitigations
- **Risk 1: `ia` CLI Tool Changes**: The `internetarchive` CLI tool itself might change its commands, output, or behavior.
  - *Mitigation*:
    - Pin the version of the `internetarchive` client if possible, or have tests that quickly detect breaking changes.
    - Design the wrapper to be adaptable, and clearly document the `ia` commands being used.
- **Risk 2: IA Service Unpredictability**: Internet Archive can have periods of instability or slow performance that are beyond the application's control.
  - *Mitigation*: Robust retry mechanisms and clear logging are the primary mitigations. The system should be designed to tolerate temporary IA unavailability and resume when IA is back online.
- **Risk 3: Complexity of Distributed Locking**: Perfect distributed locking is hard. The sentinel file approach is simple but has inherent limitations.
  - *Mitigation*:
    - For now, focus on making the existing sentinel file lock as robust as possible (timeouts, clear logging, stale lock detection/manual cleanup).
    - The current GitHub Actions workflow (one DB sync job at a time) naturally reduces concurrency risks. If workflows change to allow parallel DB syncs, the locking mechanism would need a more significant overhaul.
    - Accept that in rare, worst-case scenarios, manual intervention for the database sync might be needed.
- **Risk 4: Testing IA Interactions**: Fully testing interactions with a live external service like IA can be difficult, slow, and potentially costly (if it involved many uploads/downloads).
  - *Mitigation*:
    - Rely heavily on mocking `subprocess` calls to the `ia` CLI for unit and integration tests. Simulate different `ia` CLI outputs (success, various errors, delays).
    - Have a small number of E2E tests that do interact with a dedicated *test* item on IA, run less frequently.

## Dependencies
- `internetarchive` CLI tool (installed in the environment).
- `tenacity` (recommended for retry logic).
- `aiohttp` if direct API calls to IA were to be considered instead of `ia` CLI (not proposed for now).
- This plan interacts with the "Refactor Downloader Module" if a unified `DownloaderService` is used for IA downloads.
- Custom exceptions from `src/exceptions.py`.
