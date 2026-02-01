---
id: "20260112-104311-taskmaster-aggregate"
status: todo
title: "Taskmaster Run: src/egregora/agents/avatar.py"
created_at: "2026-01-12T10:43:11Z"
target_module: "src/egregora/agents/avatar.py"
assigned_persona: "artisan"
---

## Summary

Analysis of `src/egregora/agents/avatar.py` revealed several opportunities to improve code quality, maintainability, and robustness. The module contains complex functions with mixed responsibilities, hardcoded configuration values, and brittle logic for error handling and dependency creation. Refactoring these areas will simplify the code, making it easier to understand, test, and extend.

## Identified Tasks

### 1. Move hardcoded UUID namespace to configuration
- **Description**: The UUID namespace used for generating avatar IDs is hardcoded. This should be extracted into a configuration setting.
- **Location**: `src/egregora/agents/avatar.py:91`
- **Context**: Hardcoding values like this makes the application less flexible. Moving it to a configuration file allows for easier modification without changing the code.
- **Suggested Persona**: refactor

### 2. Decompose `download_avatar_from_url` to simplify logic
- **Description**: The `download_avatar_from_url` function is overly complex, handling URL validation, HTTP requests, content validation, and file saving in a single block. It should be broken down into smaller, single-responsibility functions.
- **Location**: `src/egregora/agents/avatar.py:289`
- **Context**: Large, complex functions are difficult to read, test, and maintain. Decomposing this function will improve clarity and make the individual components more reusable.
- **Suggested Persona**: refactor

### 3. Simplify complex error handling block
- **Description**: The `try...except` block in `download_avatar_from_url` for handling `httpx.HTTPError` is convoluted. It attempts to inspect the exception chain to re-raise specific errors, which makes the logic hard to follow.
- **Location**: `src/egregora/agents/avatar.py:340`
- **Context**: This complex error handling can likely be simplified. A clearer, more direct approach to handling download-related errors would improve the robustness and readability of the code.
- **Suggested Persona**: refactor

### 4. Decompose `_enrich_avatar` to separate concerns
- **Description**: The `_enrich_avatar` function has multiple responsibilities, including cache interaction, file loading, prompt rendering, and agent execution. This function should be refactored to separate these concerns.
- **Location**: `src/egregora/agents/avatar.py:371`
- **Context**: Similar to `download_avatar_from_url`, this function's high complexity makes it difficult to maintain. Separating concerns like caching, data preparation, and agent interaction will make the code cleaner and more modular.
- **Suggested Persona**: refactor

### 5. Use a factory or dependency injection for agent creation
- **Description**: The `_enrich_avatar` function manually creates a `pydantic-ai` Agent and its dependencies (`GoogleProvider`, `GoogleModel`). This logic is brittle and tightly couples the function to a specific implementation.
- **Location**: `src/egregora/agents/avatar.py:422`
- **Context**: Manually instantiating dependencies inside a function makes testing difficult and violates the Dependency Inversion Principle. This should be replaced with a factory function or a proper dependency injection mechanism to decouple the components.
- **Suggested Persona**: refactor
