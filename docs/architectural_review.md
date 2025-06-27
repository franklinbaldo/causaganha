# CausaGanha Project - Architectural Review

## 1. Introduction and Project Context

The CausaGanha project aims to automate the extraction, analysis, and evaluation of legal decisions from official PDF documents (Diários da Justiça) published by the Tribunal de Justiça de Rondônia (TJRO). It utilizes Google's Gemini Large Language Model (LLM) to parse these PDFs, identify key information such as case numbers, parties involved, their respective lawyers, and the outcomes of the decisions.

A core feature of the project is the application of a TrueSkill rating system, developed by Microsoft Research, to assess and rank the performance of lawyers based on the outcomes of these legal decisions. The system is designed as a batch processing pipeline, orchestrated via a command-line interface (`pipeline.py`), which handles downloading the PDFs, extracting data using the LLM, and updating lawyer ratings. These processes are automated using GitHub Actions. The data, including lawyer ratings and historical decision data, is currently stored in CSV files.

This review assesses the current architecture of the CausaGanha system, identifies its strengths and weaknesses, and provides actionable recommendations for its evolution.

## 2. Current Architecture (Post-DuckDB Migration)

The CausaGanha system has evolved into a distributed, asynchronous batch processing pipeline. Its architecture now centers on a shared DuckDB database, enabling robust, collaborative workflows between local development environments and automated GitHub Actions.

### 2.1. Core Components & Workflow

1.  **`async_diario_pipeline.py` (Primary Orchestrator)**:
    *   **Functionality**: Manages the end-to-end, concurrent processing of legal gazettes. It handles downloading PDFs from TJRO, uploading them to the Internet Archive for permanent storage, extracting structured data via the Gemini LLM, and updating the central DuckDB database.
    *   **Details**: Uses `aiohttp` for concurrent downloads and uploads. It is designed for bulk processing and can handle thousands of documents, with features for resuming interrupted jobs and tracking progress.

2.  **`ia_database_sync.py` (Distributed Database Manager)**:
    *   **Functionality**: Manages the synchronization of the central `causaganha.duckdb` database between the local filesystem and a master copy on the Internet Archive.
    *   **Details**: Implements a locking mechanism using sentinel files on the Internet Archive to prevent data corruption from simultaneous writes by different clients (e.g., a local machine and a GitHub Actions runner).

3.  **`database.py`**:
    *   **Functionality**: Provides a dedicated interface for all interactions with the DuckDB database. It encapsulates table creation, data insertion, and querying logic.
    *   **Details**: Defines the schema for all core tables (`ratings`, `partidas`, `decisoes`, `pdfs`) and ensures transactional data integrity.

4.  **`extractor.py`**:
    *   **Functionality**: Remains the core component for extracting structured JSON data from PDF gazettes using Google's Gemini LLM.
    *   **Details**: It is now called by the `async_diario_pipeline.py` and processes PDF content passed to it. Includes smart chunking for large documents and rate limiting to respect API quotas.

5.  **`ia_discovery.py`**:
    *   **Functionality**: A utility for querying the Internet Archive to discover already archived content.
    *   **Details**: It can generate reports on data coverage, identify missing documents, and provide a complete inventory of stored items, which is crucial for managing large-scale processing jobs.

### 2.2. Data Storage

*   **Primary Storage (Single Source of Truth)**: A **DuckDB database** (`data/causaganha.duckdb`). This file serves as the central, authoritative data store for all structured data, including lawyer ratings, match histories, and decision metadata.
*   **Permanent PDF Archive**: The **Internet Archive** is used for the permanent, public storage of all original PDF gazettes. This ensures transparency and reduces local storage requirements.
*   **Distributed Database Master**: A master copy of the DuckDB database is also stored on the **Internet Archive**, serving as the synchronization point for all distributed clients.
*   **CSVs (Export/Backup Only)**: CSV files are no longer used for primary data storage. Their role is limited to occasional data exports for analysis in other tools or for creating human-readable backups.

### 2.3. Automation

*   The system is fully automated via **four specialized GitHub Actions workflows**:
    *   `pipeline.yml`: Runs the daily async pipeline for recent documents.
    *   `bulk-processing.yml`: Handles large-scale, on-demand processing of historical data.
    *   `database-archive.yml`: Creates public, versioned snapshots of the database.
    *   `test.yml`: Ensures code quality through automated testing.

### 2.4. Architectural Paradigm

*   The system follows a **distributed, asynchronous batch processing architecture**. It is designed for resilience and scalability, capable of processing tens of thousands of documents in parallel across different environments while maintaining data consistency through a shared, synchronized database.

## 3. Strengths of the Current Architecture

1.  **Modularity and Separation of Concerns**: Core tasks are in distinct Python modules, promoting organization and maintainability.
1.  **Effective Automation Potential**: The CLI-driven design and existing GitHub Actions enable robust, unattended operation.
2.  **Leveraging Advanced AI**: Direct Gemini LLM integration allows sophisticated data extraction from complex legal PDFs.
3.  **Clear and Sequential Data Flow**: The `collect` -> `extract` -> `update` pipeline provides a logical and understandable data progression.
4.  **Simplicity of Initial Data Storage**: CSV files offer ease of use and inspection for the current project stage, speeding up initial development.
5.  **Focused Utility Functions**: Centralized helpers in `utils.py` (e.g., name normalization, decision validation) ensure consistency and reduce code duplication.
6.  **Extensibility for Core Logic**: Modular design allows individual components to be expanded or modified with relative ease, provided interfaces are maintained.

## 4. Weaknesses and Current Challenges

With the transition to a more robust, database-centric architecture, the system's bottlenecks have shifted from storage and basic processing to data quality, pipeline reliability, and the nuances of LLM interaction.

1.  **Advogado (Lawyer) ID Management**:
    *   **Critical Risk**: This remains the most significant challenge. The system's reliance on normalized names for the `advogado_id` is highly susceptible to errors, including collisions (different lawyers with the same name) and fragmentation (the same lawyer spelled differently). This directly compromises the integrity of the OpenSkill ratings.

2.  **LLM Dependency and Management**:
    *   **Prompt Engineering & Versioning**: The quality of extracted data is critically dependent on the prompts used with the Gemini LLM. There is currently no formal system for versioning these prompts, making it difficult to track changes and reproduce results reliably.
    *   **Cost and Performance (Lack of Caching)**: Every PDF is processed by the LLM on every run, even if the content has not changed. This incurs unnecessary API costs and slows down the pipeline. A caching mechanism for LLM responses is absent.
    *   **Output Variability**: LLMs can produce slightly different results for the same input on different occasions. The system needs to be resilient to minor variations in JSON structure or content.

3.  **Pipeline Robustness and Error Handling**:
    *   **Transient Errors**: While the asynchronous pipeline is more resilient, it needs more sophisticated handling for transient network errors, API rate limits, or temporary outages of external services like the Internet Archive.
    *   **Data Validation**: The initial `validate_decision` is a good first step, but a more comprehensive, multi-stage validation process is needed to catch subtle data quality issues before they are written to the database.
    *   **Dead-Letter Queue**: There is no formal mechanism for handling data that repeatedly fails processing. These items are currently dropped or ignored, but they should be logged to a "dead-letter queue" for manual inspection and reprocessing.

4.  **Configuration Management**:
    *   While core parameters are in `config.toml`, other important configurations (like LLM model names, specific timeouts, or feature flags) might be hardcoded within the scripts, reducing flexibility.

5.  **Automated Testing Coverage**:
    *   The test suite covers the core components, but it needs to be expanded to address the new complexities of the distributed system, such as testing the database locking mechanism, the synchronization logic, and the asynchronous processing of edge cases.

## 5. Actionable Suggestions (New Priorities)

The priorities have shifted from building the infrastructure to hardening the backend processes and ensuring data quality.

### High Priority

1.  **Implement a Robust `Advogado_ID` Strategy**:
    *   **Suggestion**: This is the highest priority. The system must move beyond normalized names. The ideal solution is to reliably extract the OAB number (lawyer's bar association number) and use it as the primary unique identifier.
    *   **Action**:
        1.  Update the LLM prompt to specifically and reliably extract the OAB number for each lawyer.
        2.  Modify the `database` schema to include an `oab` field in the `ratings` table.
        3.  Update the data processing logic to use the OAB number as the `advogado_id`.
        4.  Develop a fallback or reconciliation strategy for cases where the OAB is not available.

2.  **Implement LLM Caching**:
    *   **Suggestion**: Create a caching layer for LLM responses to avoid reprocessing the same data.
    *   **Action**:
        1.  Use the SHA-256 hash of a PDF's content as the cache key.
        2.  Before calling the Gemini API, check if a response for that hash already exists in a cache (this could be a simple key-value store or even a dedicated table in DuckDB).
        3.  If a cached response exists, use it. Otherwise, call the API and store the new response in the cache.

3.  **Establish Prompt Versioning**:
    *   **Suggestion**: Manage LLM prompts systematically.
    *   **Action**:
        1.  Store all prompts in a dedicated directory (e.g., `prompts/`).
        2.  Name prompts with version numbers (e.g., `extraction_prompt_v1.txt`, `extraction_prompt_v2.txt`).
        3.  Load the desired prompt version in the `extractor.py` script, making the version a configurable parameter.
        4.  Log which prompt version was used to process each document.

### Medium Priority

4.  **Enhance Pipeline Robustness**:
    *   **Suggestion**: Improve the resilience of the asynchronous pipeline.
    *   **Action**:
        1.  Integrate a robust retry library (like `tenacity`) for all external API calls (`aiohttp` requests, Gemini calls, Internet Archive uploads).
        2.  Implement a formal "dead-letter queue" by creating a `failed_processing` table in DuckDB to log documents that fail repeatedly, along with the error details.

5.  **Expand and Deepen Automated Testing**:
    *   **Suggestion**: Ensure the test suite covers the new distributed and asynchronous aspects of the system.
    *   **Action**:
        1.  Write integration tests that specifically target the `ia_database_sync.py` logic, including lock contention scenarios.
        2.  Add tests for the LLM caching mechanism.
        3.  Create tests for edge cases in the async pipeline, such as handling empty or corrupted PDFs.

### Low Priority (Future Considerations)

6.  **Develop a Monitoring and Alerting System**:
    *   **Suggestion**: Implement a system to monitor the health of the automated pipeline.
    *   **Action**: Use the `--stats-only` feature and other logs to generate a daily report. Set up GitHub Actions to send a notification (e.g., via email or Slack) if a workflow fails or if data anomalies are detected (e.g., a sudden drop in the number of processed decisions).

7.  **Build a User-Facing API/Dashboard**:
    *   **Suggestion**: Once the backend is sufficiently robust and the data quality is high, consider building an interface for end-users.
    *   **Action**: Develop a simple read-only API (e.g., using FastAPI) to expose the lawyer rankings and statistics. This API could then power a web-based dashboard (e.g., using Streamlit or a simple React application).

## 6. Conclusion

The CausaGanha project has established a functional pipeline for extracting legal data and applying an innovative TrueSkill-based rating system. Its current architecture demonstrates good modularity and effective automation. Configuration of the rating system has been externalized to `config.toml`, and existing automated tests have been reviewed and fixed. However, to ensure long-term viability, scalability, and reliability, continued attention to data management (especially lawyer identification and CSV storage limitations), error handling, and LLM interaction is crucial. The prioritized recommendations, particularly implementing a robust lawyer ID system, will provide a stronger foundation for the project's continued development and success.
