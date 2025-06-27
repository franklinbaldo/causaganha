# Refactor Downloader Module

## Problem Statement
- **What problem does this solve?**
  The current downloader logic, spread across `src/downloader.py` and potentially parts of `src/tribunais/tjro/collect_and_archive.py` and `src/cli.py` (archive command), might lack unified resilience, advanced error handling, and clear separation of concerns for downloading files from various sources (tribunal websites, Internet Archive).
- **Why is this important?**
  Downloading is a critical first step in the data pipeline. A robust downloader minimizes data loss, handles transient network issues gracefully, and provides clear feedback on failures. As the project expands to more tribunals and potentially other data sources, a well-structured downloader module becomes essential for maintainability and extensibility.
- **Current limitations**
  - Retry mechanisms might be basic or inconsistent.
  - Error reporting for download failures could be improved.
  - Handling of different HTTP statuses or network conditions (timeouts, connection errors) may not be comprehensive.
  - Configuration for download parameters (timeouts, retries, headers) might be scattered.
  - Logic for downloading from different types of sources (direct HTTP, IA) could be better abstracted.

## Proposed Solution
- **High-level approach**
  Refactor the existing download functionalities into a dedicated, well-structured downloader module. This module will provide a unified interface for downloading files, incorporating robust retry logic, detailed error reporting, and configurable parameters. It will also clearly distinguish between downloading source diários and fetching files from the project's IA items.
- **Technical architecture**
  1.  **`DownloaderService` Class**: A central class responsible for handling all download requests.
      - Constructor to accept configurations (max retries, backoff factor, timeout, default headers).
  2.  **Retry Mechanism**: Implement a sophisticated retry strategy (e.g., using `tenacity` library or a custom solution) with exponential backoff, jitter, and configurable number of attempts. It should retry on specific HTTP error codes (e.g., 5xx, 429) and transient network errors.
  3.  **Error Reporting**:
      - Custom exceptions like `DownloadError`, `MaxRetriesExceededError`, `UnsupportedContentTypeError`.
      - Detailed logging of download attempts, failures, and final outcomes, including URLs, status codes, and error messages.
  4.  **Content Validation**:
      - Basic validation of downloaded content (e.g., checking Content-Type header, ensuring PDF starts with `%PDF`).
  5.  **Source Abstraction (Optional but Recommended)**:
      - Potentially define interfaces or strategies for different download sources if their handling logic varies significantly (e.g., `HttpDownloaderStrategy`, `IADownloaderStrategy`). For now, focus on robust HTTP downloads.
  6.  **Async Support**: Ensure the downloader service is fully `async` compatible, using `aiohttp` for making HTTP requests.
  7.  **Configuration**: Centralize downloader configurations (timeouts, retries, user-agents) in `config.toml`.
  8.  **Integration with `Diario` dataclass**: The downloader should seamlessly integrate with the `Diario` object, updating its `pdf_path` and `status` upon successful download.

- **Implementation steps**
  1.  **Phase 1: Design and Core Implementation (Weeks 1-2)**
      - Design the `DownloaderService` class interface and its configuration options.
      - Implement the core async download logic using `aiohttp`.
      - Integrate a robust retry mechanism (e.g., research and choose `tenacity` or build a custom async-compatible one).
      - Define and implement custom downloader exceptions.
  2.  **Phase 2: Refactor Existing Download Logic (Weeks 3-4)**
      - Identify all current download functionalities (TJRO direct downloads in `collect_and_archive.py` and `cli.py archive` command, IA downloads in `analyze` command or `ia_helpers.py`).
      - Replace this logic with calls to the new `DownloaderService`.
      - Ensure the `archive` functionality in `cli.py` (or its replacement via `Diario` system) uses the new service for fetching original diários.
      - Ensure the `analyze` stage uses the service (or a specialized method within it) for fetching PDFs from Internet Archive.
  3.  **Phase 3: Configuration and Testing (Week 5)**
      - Move all relevant configurations (timeouts, retries, user-agents) to `config.toml` and ensure the `DownloaderService` uses them.
      - Write comprehensive unit tests for the `DownloaderService`, including tests for retry logic, error handling, and different download scenarios (success, various failures).
      - Write integration tests to ensure the service works correctly within the pipeline stages that use it.
  4.  **Phase 4: Documentation and Refinement (Week 6)**
      - Document the `DownloaderService`, its configurations, and usage patterns.
      - Refine error messages and logging based on testing.

## Success Criteria
- **Improved Resilience**: Downloads automatically retry on transient errors and configurable server errors, leading to fewer permanent failures.
- **Better Error Insight**: Clear and informative error messages and logs when downloads fail, aiding in debugging.
- **Maintainability**: Download logic is centralized, making it easier to update and maintain (e.g., changing User-Agent globally).
- **Configurability**: Key download parameters (timeouts, retries) are easily configurable.
- **Testability**: The downloader module is well-tested with high unit test coverage.
- **Consistency**: All parts of the application use the same robust mechanism for downloading files.
- **No Regressions**: Existing download functionalities (e.g., fetching latest TJRO diário, fetching from IA) continue to work correctly through the new service.

## Implementation Plan (High-Level for this document)
1.  **Create `DownloaderService`**: Implement the class with `aiohttp`, retry logic (`tenacity`), and custom exceptions.
2.  **Refactor TJRO Downloads**: Update `src/tribunais/tjro/downloader.py` (if using `Diario` model) or relevant parts of `cli.py`/`collect_and_archive.py` to use `DownloaderService` for fetching original diários.
3.  **Refactor IA Downloads**: Update `ia_helpers.py` or `cli.py` (analyze stage) to use `DownloaderService` for fetching PDFs from the project's IA items.
4.  **Centralize Config & Add Tests**: Move configurations to `config.toml`. Write extensive unit and integration tests. Document the module.

## Risks & Mitigations
- **Risk 1: Over-Engineering Retries**: Making the retry logic too complex or too aggressive could lead to unintended consequences (e.g., overwhelming a server).
  - *Mitigation*: Start with a sensible default retry policy (e.g., 3-5 retries, exponential backoff with a cap). Make it configurable. Follow best practices for retries (e.g., add jitter).
- **Risk 2: Handling Diverse Server Behaviors**: Different servers might have unique ways of indicating rate limits or temporary issues.
  - *Mitigation*: Allow configuration of which HTTP status codes trigger retries. Log server responses thoroughly to help diagnose issues with specific sources.
- **Risk 3: Introducing Regressions**: Changing existing download logic could break parts of the pipeline.
  - *Mitigation*:
    - Implement thorough integration tests for pipeline stages that rely on downloads.
    - Initially, the new `DownloaderService` can be introduced alongside existing logic, and then gradually replace it.
    - Test against real tribunal URLs and IA items.
- **Risk 4: Configuration Complexity**: Too many configuration options can make the downloader hard to use.
  - *Mitigation*: Provide sensible defaults for all configuration parameters. Only expose configuration for parameters that genuinely need tuning.

## Dependencies
- `aiohttp`: For asynchronous HTTP requests.
- `tenacity` (recommended): For robust retry mechanisms.
- Standard Python `logging` module.
- Custom exceptions defined in `src/exceptions.py`.
- Configuration from `config.toml`.
