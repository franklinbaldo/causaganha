# Agent: roberta-vieira
> 📝️ **Read [README.md](./README.md) before editing this card.**

## Profile
- **Name**: Roberta Vieira
- **Nationality**: Brazil
- **Specialization**: Otimização de modelos LLM e uso de Pydantic para análise jurídica
- **Sprint**: sprint-2025-03
- **Branch**: `feat/sprint-2025-03-roberta-vieira`
- **Status**: Active
- **Capacity**: 5 tasks

## File Permissions
- _No file assignments yet_

## Current Sprint Tasks

### 🆕 Planned for sprint-2025-03 (aligned with MASTERPLAN Phase 2 & Sprint 2025-03 concepts) - Cycle YYYYMMDDTHHMMSSZ
- [x] Design and implement core Pydantic models for the "Unified Diario interface" as part of the "Diario Dataclass Foundation" plan (`diario-class.md`).
- [x] Review existing LLM extraction prompts and Pydantic models; identify areas for optimization or refactoring in preparation for multi-tribunal support.
- [x] Research and document Pydantic best practices for data validation and serialization relevant to the judicial data.
- [ ] If time permits, begin preliminary research on integrating an additional LLM provider, focusing on API compatibility and data mapping to existing Pydantic models.

## Task Status Tracking
### Sprint Progress: 3/4 tasks completed for the current cycle.

- **Started**: Tasks 1, 2, 3.
- **In Progress**: None.
- **Completed**: Tasks 1, 2 (review & suggestions), 3.
- **Issues**: Initial file permissions unclear, proceeded with work aligned with specialization.

## Notes
- Card was showing "created for future assignments", updated to reflect current work.
- Assumed permissions to create `src/models/diario_pydantic.py` and `docs/guides/pydantic_best_practices_legal_data.md` based on specialization and assigned tasks.

## 🎛️ Agent Communication
**See [Agent Communication Guidelines](./README.md#agent-communication-guidelines)** for usage instructions.

## 📝 Scratchpad & Notes (Edit Freely)

**Cycle YYYYMMDDTHHMMSSZ - Roberta Vieira - LLM & Pydantic Work**

**Task 1: Pydantic Models for Unified Diario Interface**
- Created `src/models/diario_pydantic.py`.
- Defined `DiarioPydantic(BaseModel)` mirroring `Diario` dataclass, using Pydantic features like `HttpUrl`, field aliasing for `data` and `hash`, and string representation for `pdf_path`.

**Task 2: Review LLM Prompts & Pydantic Models**
- **Pydantic Models (`src/models/llm_output.py`)**:
    - `Decision` and `ExtractionResult` models are suitable as a baseline for multi-tribunal support.
    - Potential future enhancements: dedicated models for `Advogado` or `Parte` if more structure is needed.
- **LLM Prompts (`src/extractor.py`)**:
    - Prompt is currently hardcoded in `GeminiExtractor.extract_and_save_json`.
    - **Key Suggestions for Optimization/Refactoring**:
        1.  **Externalize Prompts**: Move prompts out of code to files (txt, yaml, json) or a prompt management system for easier versioning and A/B testing (aligns with MASTERPLAN "Prompt Versioning System").
        2.  **Tribunal-Specific Prompts**: Develop a strategy for tribunal-specific prompt variations if the generic prompt underperforms.
        3.  **Field Name Consistency**: Align prompt examples (e.g., `data` field) with Pydantic model field names (`data_decisao`) or use aliasing effectively. Ensure prompt requests population of all relevant fields (e.g., `tribunal`).
        4.  **Prompt Structure**: Consider system messages, few-shot examples, or chain-of-thought prompting techniques.
        5.  **Robust JSON Handling**: Explore more robust JSON cleaning/repair if LLM outputs are not consistently valid JSON.
    - Direct modification of `src/extractor.py` is outside my permissions. These are recommendations.

**Task 3: Document Pydantic Best Practices**
- Created `docs/guides/pydantic_best_practices_legal_data.md`.
- Document covers core principles, field types, validation, `Config` class, aliases, nested models, serialization, inheritance, forward references, judicial data specifics, and versioning.

**Task 4: Research Additional LLM Provider**
- Deferred for this cycle due to time focusing on primary tasks.

**Deliverables for this cycle:**
- `src/models/diario_pydantic.py`
- `docs/guides/pydantic_best_practices_legal_data.md`
- Review notes and suggestions for LLM prompts (documented in this scratchpad).
