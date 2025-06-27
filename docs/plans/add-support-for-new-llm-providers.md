# Add Support for New LLM Providers

## Problem Statement
- **What problem does this solve?**
  The current CausaGanha system is tightly coupled with Google's Gemini LLM for PDF content extraction and analysis (`src/extractor.py`). This dependency limits flexibility, prevents experimentation with other models, and poses a risk if access to Gemini changes or if other models offer better performance or cost-effectiveness for specific tasks.
- **Why is this important?**
  The LLM landscape is rapidly evolving. Having the ability to switch or A/B test different LLM providers (e.g., OpenAI's GPT models, Anthropic's Claude models, open-source models) allows the project to adapt to new advancements, optimize for cost or performance, and avoid vendor lock-in.
- **Current limitations**
  - `GeminiExtractor` is the sole implementation for LLM-based extraction.
  - Code that interacts with the LLM is specific to the Gemini API and its response structure.
  - Configuration for LLM interaction (`GEMINI_API_KEY`, model name) is Gemini-specific.

## Proposed Solution
- **High-level approach**
  Refactor the LLM interaction layer to use an adapter pattern. Define a common interface for LLM services, and implement specific adapters for each supported LLM provider (starting with Gemini, then adding others).
- **Technical architecture**
  1.  **`LLMProviderInterface` (Abstract Base Class)**:
      - Define an ABC in `src/llm/interface.py` with common methods, e.g.:
        ```python
        from abc import ABC, abstractmethod
        from typing import Dict, Any, List

        class LLMProviderInterface(ABC):
            @abstractmethod
            def __init__(self, api_key: str, model_name: str, **kwargs):
                pass

            @abstractmethod
            async def extract_data_from_text(self, text_content: str, prompt: str) -> Dict[str, Any]:
                """Extracts structured data from text using a given prompt."""
                pass

            # Potentially other methods like:
            # @abstractmethod
            # async def generate_summary(self, text_content: str) -> str:
            #     pass
        ```
  2.  **Specific Adapters**:
      - `src/llm/gemini_adapter.py`: Refactor existing `GeminiExtractor` logic into a class `GeminiAdapter` that implements `LLMProviderInterface`.
      - `src/llm/openai_adapter.py`: New adapter for OpenAI models.
      - `src/llm/claude_adapter.py`: New adapter for Anthropic Claude models.
  3.  **LLM Service Factory**:
      - A factory function or class in `src/llm/__init__.py` that instantiates the correct adapter based on configuration.
        ```python
        def get_llm_provider(config: Dict[str, Any]) -> LLMProviderInterface:
            provider_name = config.get("default_llm_provider", "gemini")
            # Load specific provider config
            # Instantiate and return the correct adapter
        ```
  4.  **Configuration (`config.toml`)**:
      - Add a general `[llm]` section and provider-specific sections:
        ```toml
        [llm]
        default_provider = "gemini" # or "openai", "claude"
        extraction_prompt_file = "current_prompt.txt" # Keep prompt separate

        [llm.gemini]
        api_key = "env:GEMINI_API_KEY" # Support reading from env
        model_name = "gemini-2.5-flash-lite-preview-06-17"

        [llm.openai]
        api_key = "env:OPENAI_API_KEY"
        model_name = "gpt-4o"

        [llm.claude]
        api_key = "env:ANTHROPIC_API_KEY"
        model_name = "claude-3-opus-20240229"
        ```
  5.  **Refactor `src/extractor.py`**:
      - Rename `extractor.py` to something more generic like `data_extractor_service.py` or have it use the `LLMProviderInterface`.
      - The core logic for chunking text, applying prompts, and handling responses will now use the `LLMProviderInterface` methods.
  6.  **Standardized Response (Optional but Recommended)**:
      - Adapters should ideally transform provider-specific responses into a standardized internal data structure (e.g., a Pydantic model) before returning. This decouples the rest of the application from the specifics of each LLM's output format.

- **Implementation steps**
  1.  **Phase 1: Interface and Gemini Adapter (Weeks 1-2)**
      - Define `LLMProviderInterface`.
      - Refactor the existing `GeminiExtractor` into `GeminiAdapter` implementing the new interface.
      - Update `config.toml` structure for LLM configuration.
      - Implement the LLM service factory.
      - Modify `src/extractor.py` (or its successor) to use the factory and interface. Ensure all existing functionality works through this abstraction.
  2.  **Phase 2: Add OpenAI Adapter (Weeks 3-4)**
      - Implement `OpenAIAdapter` for a specific OpenAI model (e.g., GPT-4o).
      - Add necessary configuration options and API key handling.
      - Write tests for the OpenAI adapter (mocking OpenAI API calls).
      - Allow switching between Gemini and OpenAI via `config.toml`.
  3.  **Phase 3: Add Anthropic Claude Adapter (Weeks 5-6)**
      - Implement `ClaudeAdapter` for a specific Claude model.
      - Add configuration and API key handling.
      - Write tests for the Claude adapter.
  4.  **Phase 4: Standardized Response Model & Documentation (Week 7)**
      - If not done earlier, define a Pydantic model for the standardized LLM extraction output.
      - Ensure all adapters transform their native responses to this model.
      - Document how to add new LLM provider adapters and configure them.
  5.  **Phase 5: A/B Testing Framework (Optional Future Enhancement)**
      - Consider adding a mechanism to easily A/B test different LLMs on the same documents and compare results/costs.

## Success Criteria
- **Provider Agnostic**: The core application logic in `src/extractor.py` (or its successor) interacts with LLMs via `LLMProviderInterface` and is unaware of the specific provider being used.
- **Multiple Providers Supported**: At least two LLM providers (e.g., Gemini and OpenAI) are successfully integrated and can be selected via configuration.
- **Configuration Driven**: The active LLM provider and its model are chosen based on `config.toml` settings.
- **Maintainability**: Adding a new LLM provider primarily involves creating a new adapter class and updating configuration, with minimal changes to core logic.
- **Testability**: Each adapter can be tested independently by mocking its respective external API.
- **No Regression**: Existing LLM-based extraction functionality (using Gemini) remains fully operational through the new abstraction layer.

## Implementation Plan (High-Level for this document)
1.  **Define Interface & Refactor Gemini**: Create `LLMProviderInterface`. Convert `GeminiExtractor` to `GeminiAdapter`. Update config and `extractor.py` to use the interface.
2.  **Implement OpenAI Adapter**: Create `OpenAIAdapter`, add its config, and test.
3.  **Implement Claude Adapter**: Create `ClaudeAdapter`, add its config, and test.
4.  **Standardize Response (Pydantic)**: Define a common output model. Ensure adapters map to it. Document.

## Risks & Mitigations
- **Risk 1: Diverging LLM Capabilities**: Different LLMs have varying strengths, weaknesses, prompt syntaxes, and API features (e.g., tool use, system prompts). A purely generic interface might not leverage all features of a specific LLM.
  - *Mitigation*:
    - Design the interface around common core tasks (e.g., text extraction based on a prompt).
    - Allow `**kwargs` in interface methods for provider-specific parameters.
    - If advanced features are needed, the interface might need to be extended, or specific tasks might still require provider-aware logic at a higher level.
- **Risk 2: Prompt Engineering Variations**: Prompts often need to be tailored for optimal performance with different LLMs.
  - *Mitigation*: The `extraction_prompt_file` can still be specific. The system could support provider-specific prompts if necessary (e.g., `gemini_extraction_prompt.txt`, `openai_extraction_prompt.txt`) and load the appropriate one. The "Prompt Versioning Strategy" plan needs to accommodate this.
- **Risk 3: Inconsistent Response Structures**: LLMs return data in different JSON structures or formats.
  - *Mitigation*: This is a key area for the adapter to handle. Each adapter is responsible for transforming the provider's native response into a standardized internal format (ideally a Pydantic model). This is crucial for decoupling.
- **Risk 4: API Key Management**: Managing API keys for multiple providers securely.
  - *Mitigation*: Continue using environment variables for API keys (`env:GEMINI_API_KEY`). Ensure `.env.example` lists all potential keys. Securely manage these in CI/CD environments.
- **Risk 5: Cost Management**: Different LLMs have different pricing.
  - *Mitigation*: The choice of LLM provider will be configurable. The project should track costs associated with each provider if usage becomes significant. This plan focuses on technical integration, not cost optimization strategies.

## Dependencies
- New HTTP client libraries might be needed for different LLM providers (e.g., `openai` Python library, `anthropic` Python library).
- `pydantic` for standardized response models.
- This plan should align with the "Prompt Versioning Strategy" to manage prompts effectively, potentially with provider-specific prompt variants.
