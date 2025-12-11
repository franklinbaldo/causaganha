# Pydantic AI Integration for Extractor

## Problem Statement

- **Fragile Extraction**: The current `extractor.py` relies on raw string prompting and manual JSON parsing/repairing, which is error-prone.
- **Type Safety**: There is no guarantee that the LLM output matches the internal data structures expected by the application.
- **Maintenance**: Prompt engineering for strict JSON output is difficult to maintain and debug.
- **Validation**: Validation logic is mixed with extraction logic.

## Proposed Solution

- **Use pydantic-ai**: Integrate `pydantic-ai` to handle the interaction with the Gemini API.
- **Structured Output**: Define Pydantic models for the expected extraction result. `pydantic-ai` ensures the LLM output matches these models.
- **Separation of Concerns**: Separate the schema definition from the extraction logic.
- **Robustness**: Leverage `pydantic-ai`'s built-in validation and retry mechanisms.

## Technical Architecture

- **`src/schemas.py`**: A new module to hold Pydantic models (`Decision`, `DecisionResult`, etc.).
- **`src/extractor.py`**: Refactored to use `pydantic_ai.Agent`.
- **Gemini Integration**: Use `pydantic-ai`'s support for Gemini (via `google-generativeai` or Vertex AI).

## Success Criteria

- **Functional Parity**: The new extractor must extract at least the same amount of information as the old one.
- **Type Safety**: The output of the extractor must be validated Pydantic objects.
- **Tests Passing**: Existing tests (updated) must pass.
- **Clean Code**: Reduced complexity in `extractor.py` regarding JSON parsing.

## Implementation Plan

1.  **Dependency**: Add `pydantic-ai` to the project.
2.  **Schema Definition**: Create `src/schemas.py` with `Decision` and related models.
3.  **Refactor Extractor**: Rewrite `GeminiExtractor.extract_and_save_json` to use the `Agent`.
4.  **Testing**: Update unit tests to mock the `Agent` and verify extraction.
5.  **Integration**: Verify with a real PDF (if possible/allowed) or a sample text.

## Risks & Mitigations

- **Token Usage**: Structured output prompts might use more tokens. *Mitigation*: Monitor usage; the tradeoff for reliability is usually worth it.
- **Model Compatibility**: Ensure the Gemini model used supports the structured output features required by `pydantic-ai`. *Mitigation*: Use the latest stable model or fallback to standard prompting if needed (though `pydantic-ai` handles this well).
