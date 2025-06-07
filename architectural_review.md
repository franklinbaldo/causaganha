# CausaGanha Project - Architectural Review

## 1. Introduction and Project Context

The CausaGanha project aims to automate the extraction, analysis, and evaluation of legal decisions from official PDF documents (Diários da Justiça) published by the Tribunal de Justiça de Rondônia (TJRO). It utilizes Google's Gemini Large Language Model (LLM) to parse these PDFs, identify key information such as case numbers, parties involved, their respective lawyers, and the outcomes of the decisions.

A core feature of the project is the application of an Elo rating system, traditionally used in chess, to assess and rank the performance of lawyers based on the outcomes of these legal decisions. The system is designed as a batch processing pipeline, orchestrated via a command-line interface (`pipeline.py`), which handles downloading the PDFs, extracting data using the LLM, and updating lawyer ratings. These processes are automated using GitHub Actions. The data, including lawyer ratings and historical decision data, is currently stored in CSV files, with stated future plans to migrate to a relational database.

This review assesses the current architecture of the CausaGanha system, identifies its strengths and weaknesses, and provides actionable recommendations for its evolution.

## 2. Current Architecture

The CausaGanha system is a Python-based batch processing pipeline. Its architecture revolves around scripts within the `causaganha.core` module, orchestrated by `pipeline.py` which provides a Command Line Interface (CLI).

### 2.1. Core Components & Workflow

1.  **`downloader.py`**:
    *   **Functionality**: Fetches official legal gazettes (Diários da Justiça) in PDF format from the TJRO website.
    *   **Details**: Downloads gazettes for specific dates or the latest available. Uses the `requests` library.
    *   **Integration**: Optionally uploads downloaded PDFs to Google Drive via `gdrive.py`.

2.  **`gdrive.py`**:
    *   **Functionality**: Uploads files (downloaded PDFs) to a Google Drive folder.
    *   **Details**: Uses Google API client libraries and service account credentials (via environment variables `GDRIVE_SERVICE_ACCOUNT_JSON`, `GDRIVE_FOLDER_ID`).

3.  **`extractor.py`**:
    *   **Functionality**: Extracts structured JSON data from PDF gazettes using Google's Gemini LLM.
    *   **Details**: Uploads PDF content to Gemini, prompts the LLM for case details (number, parties, lawyers, outcome, date), and parses the JSON response. Includes error handling and a dummy data fallback if Gemini is not configured (requires `GEMINI_API_KEY` environment variable).

4.  **`utils.py`**:
    *   **Functionality**: Contains helper functions for data processing.
    *   **`normalize_lawyer_name()`**: Standardizes lawyer names (lowercase, removes titles, normalizes accents, cleans whitespace).
    *   **`validate_decision()`**: Validates extracted JSON data for essential fields (`numero_processo`, `partes`, `resultado`) and basic format criteria.

5.  **`elo.py`**:
    *   **Functionality**: Implements the Elo rating algorithm.
    *   **Details**: Calculates new Elo ratings for two lawyers based on current ratings, decision outcome (win/loss/draw for "requerente"), and a K-factor (fixed at 16). Default initial rating is 1500.

6.  **`pipeline.py` (CLI Orchestrator)**:
    *   **Functionality**: Central script defining the operational workflow via a CLI, integrating other components.
    *   **Commands**:
        *   `collect --date <YYYY-MM-DD>`: Downloads PDF for the date (uses `downloader.py`).
        *   `extract --pdf_file <path>`: Processes a PDF to JSON (uses `extractor.py`).
        *   `update`: Core data processing. Reads extracted JSONs, normalizes lawyer names, validates decisions, pairs lawyers, determines match outcomes, updates Elo ratings (uses `elo.py`), and records matches.
        *   `run --date <YYYY-MM-DD>`: Executes `collect`, `extract`, and `update` sequentially.
    *   **Output**: The `update` process manages two main CSV files:
        *   `causaganha/data/ratings.csv`: Current Elo rating and total matches per lawyer.
        *   `causaganha/data/partidas.csv`: Historical log of processed decisions/matches.
    *   **File Management**: Moves processed JSONs from `causaganha/data/json/` to `causaganha/data/json_processed/`.

### 2.2. Data Storage

*   **PDFs**: Original gazettes in `causaganha/data/diarios/`.
*   **Extracted JSON (Raw)**: LLM output stored in `causaganha/data/json/` before processing.
*   **Processed JSON**: Moved to `causaganha/data/json_processed/` post-update.
*   **Ratings & Match History**: Stored in `causaganha/data/ratings.csv` and `causaganha/data/partidas.csv`.

### 2.3. Automation

*   The system is designed for automation. GitHub Actions (`01_collect.yml`, `02_extract.yml`, `03_update.yml`) are used to schedule and run the pipeline daily.

### 2.4. Architectural Paradigm

*   The system follows a **batch processing architecture**. It is not a real-time service and currently does not expose user-facing APIs for on-demand requests.

## 3. Strengths of the Current Architecture

1.  **Modularity and Separation of Concerns**: Core tasks are in distinct Python modules, promoting organization and maintainability.
2.  **Effective Automation Potential**: The CLI-driven design and existing GitHub Actions enable robust, unattended operation.
3.  **Leveraging Advanced AI**: Direct Gemini LLM integration allows sophisticated data extraction from complex legal PDFs.
4.  **Clear and Sequential Data Flow**: The `collect` -> `extract` -> `update` pipeline provides a logical and understandable data progression.
5.  **Simplicity of Initial Data Storage**: CSV files offer ease of use and inspection for the current project stage, speeding up initial development.
6.  **Focused Utility Functions**: Centralized helpers in `utils.py` (e.g., name normalization, decision validation) ensure consistency and reduce code duplication.
7.  **Extensibility for Core Logic**: Modular design allows individual components to be expanded or modified with relative ease, provided interfaces are maintained.

## 4. Weaknesses and Areas for Improvement

1.  **Error Handling and Resilience**:
    *   Basic error handling (logging, halting steps) lacks robustness for transient network errors or unexpected LLM outputs. Limited retry mechanisms.
2.  **Scalability Limitations**:
    *   **Data Storage**: CSV files (`ratings.csv`, `partidas.csv`) will face performance and integrity issues with data growth. No concurrency control.
    *   **Sequential Processing**: Predominantly sequential operations can lead to long processing times for large datasets.
3.  **LLM Dependency and Management**:
    *   **Cost/Rate Limits**: No caching for LLM responses increases API call frequency. Susceptible to Gemini API rate limits.
    *   **Prompt Engineering & Output Variability**: LLM output quality is highly dependent on prompts, which may need ongoing refinement. Handling of LLM output variations could be improved. No prompt versioning.
    *   **API Changes**: External API changes can break extraction logic.
4.  **Data Validation and Integrity**:
    *   `validate_decision` is a good start but more comprehensive validation (data types, formats, consistency) is needed. Strategy for handling semantically incorrect data is unclear.
5.  **Advogado (Lawyer) ID Management**:
    *   **Critical Risk**: Current reliance on normalized names for `advogado_id` is prone to errors (e.g., lawyers with the same name), directly impacting Elo rating integrity.
6.  **Configuration Management**:
    *   Many configurations (K-factor, default ratings, paths) are hardcoded, affecting maintainability. API keys are via environment variables (standard).
7.  **Automated Testing Coverage**:
    *   While `pytest` is present, the extent of unit and integration test coverage appears limited, which is a risk for data-sensitive calculations.
8.  **Lack of Granular Asynchronous Operations**:
    *   Long-running I/O-bound tasks within pipeline steps (e.g., multiple LLM calls, processing many JSONs) are generally synchronous, impacting step performance.

## 5. Actionable Suggestions (Prioritized)

### High Priority

1.  **Transition to a Relational Database**:
    *   **Suggestion**: Migrate `ratings` and `partidas` data from CSVs to PostgreSQL (as per README future plans).
    *   **Rationale**: Addresses scalability, data integrity, and querying efficiency.
    *   **Action**: Design schema, modify `pipeline.py` and `elo.py` for DB interaction, plan CSV data migration.

2.  **Implement a Robust `Advogado_ID` Strategy**:
    *   **Suggestion**: Develop a reliable unique lawyer identification system beyond normalized names.
    *   **Rationale**: Critical for Elo rating accuracy.
    *   **Action**: Prioritize extracting and validating OAB numbers. If unfeasible, implement an internal UUID system with careful deduplication logic and a lawyer profile table. Update `pipeline.py` accordingly.

3.  **Enhance Error Handling & Implement Retry Mechanisms**:
    *   **Suggestion**: Improve error handling for I/O operations and critical data processing.
    *   **Rationale**: Increases system resilience and reduces manual intervention.
    *   **Action**: Implement retry logic (e.g., using `tenacity`) for `downloader.py` and `extractor.py` (network/API calls). In `pipeline.py`, allow processing to continue with other files if one fails, with comprehensive logging. Consider a "dead-letter queue" for repeatedly failing data.

### Medium Priority

4.  **Introduce Asynchronous Processing or Parallelism**:
    *   **Suggestion**: Explore asynchronous operations for I/O-bound tasks.
    *   **Rationale**: Improves performance for large batch processing.
    *   **Action**: For `extractor.py` (multiple LLM calls) consider `asyncio`. For `pipeline.py` (`update_command` processing many JSONs), explore `multiprocessing` or `concurrent.futures`.

5.  **Optimize LLM Interaction & Management**:
    *   **Suggestion**: Implement LLM cost reduction strategies and better prompt/response management.
    *   **Rationale**: Controls operational costs and improves extraction reliability.
    *   **Action**: Implement caching for Gemini responses (e.g., based on PDF hash). Externalize and version control LLM prompts. Use Pydantic for validating LLM JSON output structure.

6.  **Expand Automated Test Coverage**:
    *   **Suggestion**: Significantly increase unit and integration tests.
    *   **Rationale**: Ensures code quality and correctness, especially for Elo logic.
    *   **Action**: Write comprehensive unit tests for all core modules. Develop integration tests for `pipeline.py` commands with mocked external services.

7.  **Centralized Configuration Management**:
    *   **Suggestion**: Move non-secret configurations to a dedicated file (YAML, TOML).
    *   **Rationale**: Improves maintainability and flexibility.
    *   **Action**: Load settings from a config file at application startup in `pipeline.py`.

### Low Priority (Future Considerations)

8.  **Implement Monitoring and Alerting**:
    *   **Suggestion**: Add basic monitoring for automated GitHub Actions runs.
    *   **Rationale**: Proactively informs about pipeline failures or data anomalies.
    *   **Action**: Log key metrics; set up notifications for workflow failures in GitHub Actions.

9.  **Develop an API Layer (If Needed)**:
    *   **Suggestion**: If real-time access or UI integration is planned, build a dedicated API layer (e.g., using FastAPI).
    *   **Rationale**: Decouples core logic and provides a structured interface.

## 6. Conclusion

The CausaGanha project has established a functional pipeline for extracting legal data and applying an innovative Elo-based rating system. Its current architecture demonstrates good modularity and effective automation. However, to ensure long-term viability, scalability, and reliability, addressing weaknesses in data management (especially lawyer identification and CSV storage), error handling, and LLM interaction is crucial. The prioritized recommendations, particularly transitioning to a relational database and implementing a robust lawyer ID system, will provide a stronger foundation for the project's continued development and success.
