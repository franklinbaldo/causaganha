# CausaGanha Project - Architectural Review

## 1. Introduction and Project Context

The CausaGanha project aims to automate the extraction, analysis, and evaluation of legal decisions from official PDF documents (Diários da Justiça) published by the Tribunal de Justiça de Rondônia (TJRO). It utilizes Google's Gemini Large Language Model (LLM) to parse these PDFs, identify key information such as case numbers, parties involved, their respective lawyers, and the outcomes of the decisions.

A core feature of the project is the application of a TrueSkill rating system, developed by Microsoft Research, to assess and rank the performance of lawyers based on the outcomes of these legal decisions. The system is designed as a batch processing pipeline, orchestrated via a command-line interface (`pipeline.py`), which handles downloading the PDFs, extracting data using the LLM, and updating lawyer ratings. These processes are automated using GitHub Actions. The data, including lawyer ratings and historical decision data, is currently stored in CSV files.

This review assesses the current architecture of the CausaGanha system, identifies its strengths and weaknesses, and provides actionable recommendations for its evolution.

## 2. Current Architecture

The CausaGanha system is a Python-based batch processing pipeline. Its architecture revolves around scripts within the `causaganha.core` module, orchestrated by `pipeline.py` which provides a Command Line Interface (CLI).

### 2.1. Core Components & Workflow

1.  **`downloader.py`**:
    *   **Functionality**: Fetches official legal gazettes (Diários da Justiça) in PDF format from the TJRO website.
    *   **Details**: Downloads gazettes for specific dates or the latest available. Uses the `requests` library.
    *   **Integration**: Optionally uploads downloaded PDFs to Google Drive via `gdrive.py`.

1.  **`gdrive.py`**:
    *   **Functionality**: Uploads files (downloaded PDFs) to a Google Drive folder.
    *   **Details**: Uses Google API client libraries and service account credentials (via environment variables `GDRIVE_SERVICE_ACCOUNT_JSON`, `GDRIVE_FOLDER_ID`).

2.  **`extractor.py`**:
    *   **Functionality**: Extracts structured JSON data from PDF gazettes using Google's Gemini LLM.
    *   **Details**: Uploads PDF content to Gemini, prompts the LLM for case details (number, parties, lawyers, outcome, date), and parses the JSON response. Includes error handling and a dummy data fallback if Gemini is not configured (requires `GEMINI_API_KEY` environment variable).

3.  **`utils.py`**:
    *   **Functionality**: Contains helper functions for data processing.
    *   **`normalize_lawyer_name()`**: Standardizes lawyer names (lowercase, removes titles, normalizes accents, cleans whitespace).
    *   **`validate_decision()`**: Validates extracted JSON data for essential fields (`numero_processo`, `polo_ativo`, `polo_passivo`, `resultado`) and basic format criteria, accommodating the data structure from `extractor.py`.

4.  **`trueskill_rating.py`**:
    *   **Functionality**: Implements the TrueSkill rating algorithm.
    *   **Details**: Calculates new TrueSkill ratings (`mu` and `sigma`) for teams of lawyers based on current ratings and decision outcome. Supports teams of varying sizes. Environment parameters (initial `mu`, `sigma`, `beta`, `tau`, `draw_probability`) are configurable via `config.toml`.

5.  **`pipeline.py` (CLI Orchestrator)**:
    *   **Functionality**: Central script defining the operational workflow via a CLI, integrating other components.
    *   **Commands**:
        *   `collect --date <YYYY-MM-DD>`: Downloads PDF for the date (uses `downloader.py`).
        *   `extract --pdf_file <path>`: Processes a PDF to JSON (uses `extractor.py`).
        *   `update`: Core data processing. Reads extracted JSONs, normalizes lawyer names, validates decisions, forms lawyer teams, determines match outcomes, updates TrueSkill ratings (uses `trueskill_rating.py`), and records matches.
        *   `run --date <YYYY-MM-DD>`: Executes `collect`, `extract`, and `update` sequentially.
    *   **Output**: The `update` process manages two main CSV files and uses one configuration file:
        *   `data/ratings.csv`: Current TrueSkill ratings (`mu`, `sigma`) and total matches per lawyer.
        *   `data/partidas.csv`: Historical log of processed decisions/matches, including team compositions and ratings before/after.
        *   `config.toml`: Configuration for TrueSkill environment parameters.
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
1.  **Effective Automation Potential**: The CLI-driven design and existing GitHub Actions enable robust, unattended operation.
2.  **Leveraging Advanced AI**: Direct Gemini LLM integration allows sophisticated data extraction from complex legal PDFs.
3.  **Clear and Sequential Data Flow**: The `collect` -> `extract` -> `update` pipeline provides a logical and understandable data progression.
4.  **Simplicity of Initial Data Storage**: CSV files offer ease of use and inspection for the current project stage, speeding up initial development.
5.  **Focused Utility Functions**: Centralized helpers in `utils.py` (e.g., name normalization, decision validation) ensure consistency and reduce code duplication.
6.  **Extensibility for Core Logic**: Modular design allows individual components to be expanded or modified with relative ease, provided interfaces are maintained.

## 4. Weaknesses and Areas for Improvement

1.  **Error Handling and Resilience**:
    *   Basic error handling (logging, halting steps) lacks robustness for transient network errors or unexpected LLM outputs. Limited retry mechanisms.
1.  **Scalability Limitations**:
    *   **Data Storage**: CSV files (`ratings.csv`, `partidas.csv`) will face performance and integrity issues with data growth. No concurrency control.
    *   **Sequential Processing**: Predominantly sequential operations can lead to long processing times for large datasets.
2.  **LLM Dependency and Management**:
    *   **Cost/Rate Limits**: No caching for LLM responses increases API call frequency. Susceptible to Gemini API rate limits.
    *   **Prompt Engineering & Output Variability**: LLM output quality is highly dependent on prompts, which may need ongoing refinement. Handling of LLM output variations could be improved. No prompt versioning.
    *   **API Changes**: External API changes can break extraction logic.
3.  **Data Validation and Integrity**:
    *   `validate_decision` is a good start but more comprehensive validation (data types, formats, consistency) is needed. Strategy for handling semantically incorrect data is unclear. (Note: `validate_decision` was updated to handle new `polo_ativo`/`polo_passivo` fields).
4.  **Advogado (Lawyer) ID Management**:
    *   **Critical Risk**: Current reliance on normalized names for `advogado_id` is prone to errors (e.g., lawyers with the same name), directly impacting TrueSkill rating integrity.
5.  **Configuration Management**:
    *   TrueSkill environment parameters (initial ratings, beta, tau, draw probability) are now configurable via `config.toml`. Other configurations like file paths might still be hardcoded or use defaults. API keys are via environment variables (standard).
6.  **Automated Testing Coverage**:
    *   The existing test suite (`pytest`) was reviewed, and all tests were made to pass. This involved correcting test logic, mocks, and minor code adjustments in the application. While all existing tests pass, further expansion of test coverage for edge cases and deeper integration scenarios is always beneficial.
7.  **Lack of Granular Asynchronous Operations**:
    *   Long-running I/O-bound tasks within pipeline steps (e.g., multiple LLM calls, processing many JSONs) are generally synchronous, impacting step performance. (Note: A previous `todo` item for parallelism was de-prioritized).

## 5. Actionable Suggestions (Prioritized)

### High Priority

1.  **Implement a Robust `Advogado_ID` Strategy**:
    *   **Suggestion**: Develop a reliable unique lawyer identification system beyond normalized names.
    *   **Rationale**: Critical for Elo rating accuracy.
    *   **Action**: Prioritize extracting and validating OAB numbers. If unfeasible, implement an internal UUID system with careful deduplication logic and a lawyer profile table. Update `pipeline.py` accordingly.

2.  **Enhance Error Handling & Implement Retry Mechanisms**:
    *   **Suggestion**: Improve error handling for I/O operations and critical data processing.
    *   **Rationale**: Increases system resilience and reduces manual intervention.
    *   **Action**: Implement retry logic (e.g., using `tenacity`) for `downloader.py` and `extractor.py` (network/API calls). In `pipeline.py`, allow processing to continue with other files if one fails, with comprehensive logging. Consider a "dead-letter queue" for repeatedly failing data.

### Medium Priority

3.  **Introduce Asynchronous Processing or Parallelism**:
    *   **Suggestion**: Explore asynchronous operations for I/O-bound tasks. (Note: This was de-prioritized based on recent feedback).
    *   **Rationale**: Improves performance for large batch processing.
    *   **Action**: For `extractor.py` (multiple LLM calls) consider `asyncio`. For `pipeline.py` (`update_command` processing many JSONs), explore `multiprocessing` or `concurrent.futures`.

4.  **Optimize LLM Interaction & Management**:
    *   **Suggestion**: Implement LLM cost reduction strategies and better prompt/response management.
    *   **Rationale**: Controls operational costs and improves extraction reliability.
    *   **Action**: Implement caching for Gemini responses (e.g., based on PDF hash). Externalize and version control LLM prompts. Use Pydantic for validating LLM JSON output structure.

5.  **Maintain and Expand Automated Test Coverage**:
    *   **Suggestion**: Continue to maintain high test coverage and expand with new features.
    *   **Rationale**: Ensures code quality and correctness, especially for TrueSkill logic and data processing.
    *   **Action**: All existing unit tests were reviewed and fixed. Write new unit and integration tests for new functionalities.

6.  **Centralized Configuration Management**:
    *   **Suggestion**: Continue externalizing configurations as appropriate.
    *   **Rationale**: Improves maintainability and flexibility.
    *   **Action**: TrueSkill parameters are now in `config.toml`. Evaluate other hardcoded values (e.g., paths, LLM model names if they change frequently) for externalization.

### Low Priority (Future Considerations)

7.  **Implement Monitoring and Alerting**:
    *   **Suggestion**: Add basic monitoring for automated GitHub Actions runs.
    *   **Rationale**: Proactively informs about pipeline failures or data anomalies.
    *   **Action**: Log key metrics; set up notifications for workflow failures in GitHub Actions.

8.  **Develop an API Layer (If Needed)**:
    *   **Suggestion**: If real-time access or UI integration is planned, build a dedicated API layer (e.g., using FastAPI).
    *   **Rationale**: Decouples core logic and provides a structured interface.

## 6. Conclusion

The CausaGanha project has established a functional pipeline for extracting legal data and applying an innovative TrueSkill-based rating system. Its current architecture demonstrates good modularity and effective automation. Configuration of the rating system has been externalized to `config.toml`, and existing automated tests have been reviewed and fixed. However, to ensure long-term viability, scalability, and reliability, continued attention to data management (especially lawyer identification and CSV storage limitations), error handling, and LLM interaction is crucial. The prioritized recommendations, particularly implementing a robust lawyer ID system, will provide a stronger foundation for the project's continued development and success.
