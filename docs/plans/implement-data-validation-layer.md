# Implement Data Validation Layer

## Problem Statement
- **What problem does this solve?**
  Data flowing through the CausaGanha pipeline (from URLs, to PDFs, to extracted JSON, to database records, to OpenSkill inputs) may not be consistently validated for correctness, completeness, or adherence to expected formats. This can lead to errors in later stages, data corruption, or inaccurate results.
- **Why is this important?**
  A dedicated data validation layer ensures data quality and integrity throughout the pipeline. It helps catch errors early, prevents the propagation of bad data, makes debugging easier, and increases confidence in the final outputs (like OpenSkill ratings).
- **Current limitations**
  - Validation might be ad-hoc, scattered across different modules, or missing entirely for certain data points.
  - The `validate_decision` function in `utils.py` is a good start but might not cover all data types or stages.
  - No systematic way to define and enforce schemas for data structures like extracted JSON from LLMs or records being inserted into the database.
  - Errors due to invalid data format might lead to cryptic exceptions or silent failures.

## Proposed Solution
- **High-level approach**
  Implement a comprehensive data validation layer using a library like Pydantic. Define Pydantic models for key data structures at different pipeline stages and use these models to parse, validate, and serialize data.
- **Technical architecture**
  1.  **Pydantic Models**:
      - Define Pydantic models for:
          - Input URLs/CSV rows (e.g., `QueuedItemInput`).
          - `Diario` dataclass attributes (if not already using Pydantic, consider migrating or wrapping).
          - Configuration settings from `config.toml`.
          - LLM extraction output (JSON structure for decisions, parties, lawyers).
          - Data being inserted into DuckDB tables (e.g., `DecisionRecord`, `RatingRecord`).
          - Data read from DuckDB before being used in critical calculations (e.g., OpenSkill input).
  2.  **Validation Points**:
      - Integrate Pydantic model validation at key data ingress/egress points:
          - When queuing new items (CLI `queue` command).
          - After LLM extraction (parsing the raw JSON string).
          - Before writing to DuckDB tables.
          - After reading from DuckDB tables before use in sensitive logic.
          - When loading configurations.
  3.  **Error Handling for Validation Failures**:
      - Catch Pydantic's `ValidationError`.
      - Log detailed validation errors (field, error type, input data).
      - Implement strategies for handling validation failures:
          - Rejecting the data item.
          - Moving it to a "quarantine" or "failed_validation" state/table for later inspection.
          - Attempting data cleaning/coercion if appropriate and safe.
  4.  **Schema Evolution**:
      - Pydantic models also serve as clear schemas. Version control will track changes to these models, providing a history of schema evolution.
  5.  **Integration with `Diario` dataclass**:
      - The `Diario` dataclass can be refactored to be a Pydantic model itself, or have its attributes validated by Pydantic models at creation or update.
      - Metadata within the `Diario` object can also be validated against a Pydantic model.

- **Implementation steps**
  1.  **Phase 1: Pydantic Integration and Core Models (Weeks 1-2)**
      - Add Pydantic as a project dependency.
      - Define Pydantic models for the LLM extraction output (the most complex and critical data structure).
      - Define Pydantic models for the main DuckDB tables (`decisoes`, `ratings`, `partidas`, `job_queue`).
  2.  **Phase 2: Validate LLM Output and Database Writes (Weeks 3-4)**
      - In `src/extractor.py` (or equivalent), parse the raw JSON string from Gemini into the defined Pydantic model. Handle `ValidationError` if parsing fails.
      - Before any `INSERT` or `UPDATE` operations in `src/database.py` or CLI commands, validate the data against the corresponding Pydantic model.
  3.  **Phase 3: Validate Inputs and Configurations (Week 5)**
      - Implement validation for inputs to the `causaganha queue` command (e.g., URL format, CSV structure).
      - Use Pydantic to load and validate `config.toml` settings.
  4.  **Phase 4: Validate Database Reads and Reporting (Week 6)**
      - When reading data from DuckDB for critical operations (e.g., OpenSkill calculations, stats reporting), validate it against Pydantic models to ensure consistency.
      - Implement a mechanism to report or quarantine data that fails validation.
  5.  **Phase 5: Documentation and Refinement (Ongoing)**
      - Document all Pydantic models and the validation strategy.
      - Review and refine validation rules based on operational experience.

## Success Criteria
- **Improved Data Quality**: Significant reduction in errors caused by malformed or inconsistent data.
- **Early Error Detection**: Data validation issues are caught early in the pipeline, preventing propagation.
- **Clear Schemas**: Pydantic models serve as explicit, version-controlled schemas for key data structures.
- **Robustness**: The pipeline is more resilient to unexpected data formats from external sources (LLM, tribunal websites).
- **Easier Debugging**: Validation errors provide clear information about what went wrong with the data.
- **Increased Confidence**: Higher confidence in the accuracy of processed data and final results.
- **Validation Reporting**: A system is in place to log and potentially quarantine data that fails validation.

## Implementation Plan (High-Level for this document)
1.  **Integrate Pydantic & Define Core Models**: Add Pydantic. Create models for LLM JSON output and main DB tables.
2.  **Validate LLM Output & DB Writes**: In `extractor.py`, parse LLM JSON with Pydantic. Before DB writes, validate data with Pydantic models.
3.  **Validate Inputs & Config**: Validate `queue` command inputs and `config.toml` using Pydantic.
4.  **Validate DB Reads & Reporting**: Validate data read from DB before critical use. Implement validation failure reporting/quarantine.
5.  **Document**: Document Pydantic models and validation strategy.

## Risks & Mitigations
- **Risk 1: Performance Overhead**: Pydantic validation adds some performance overhead, especially for large datasets or frequent operations.
  - *Mitigation*:
    - Apply validation strategically at critical boundaries rather than excessively everywhere.
    - Pydantic is generally performant, but if specific models become bottlenecks, explore options like using `TypedDict` for internal type hints where full validation isn't needed, or optimizing model structure.
    - Benchmark critical paths after Pydantic integration.
- **Risk 2: Model Maintenance**: Pydantic models need to be kept in sync with evolving data structures and LLM outputs.
  - *Mitigation*:
    - Treat Pydantic models as a core part of the application's contract. Update them as part of any changes to data structures.
    - Good test coverage for code that uses these models will help catch inconsistencies.
- **Risk 3: Overly Strict Validation**: Validation rules that are too strict might reject valid data, especially from varied sources like different tribunals or evolving LLM outputs.
  - *Mitigation*:
    - Design models with flexibility where appropriate (e.g., use `Optional` fields, unions, or default values).
    - Implement a clear process for handling validation failures, including manual review and model updates if necessary.
    - Start with essential validation and gradually add more specific rules.
- **Risk 4: Complexity in Defining Models**: For very complex or dynamic JSON structures, defining Pydantic models can be challenging.
  - *Mitigation*:
    - Break down complex models into smaller, nested models.
    - Use Pydantic features like `root_validator` or custom data types for complex validation logic.
    - For highly dynamic structures, validate only the known/required parts.

## Dependencies
- `pydantic`: The core library for data validation.
- This plan integrates well with the "Improve Error Handling and Logging" plan, as `ValidationError` would be one of the custom exceptions to handle and log.
