---
id: "20260105-013431-taskmaster-aggregate"
status: todo
title: "Taskmaster Run: src/egregora/agents/taxonomy.py"
created_at: "2026-01-05T01:34:31Z"
target_module: "src/egregora/agents/taxonomy.py"
assigned_persona: "taskmaster"
---

## Summary

This run analyzed `src/egregora/agents/taxonomy.py` and identified several minor code quality issues. The agent creator function uses function-level imports which is unconventional, the Pydantic models lack detailed docstrings, and there's a brittle hardcoded string manipulation for the model name. Addressing these will improve the clarity and robustness of this module.

## Identified Tasks

### 1. Move function-level imports to top of file
- **Description**: The `create_global_taxonomy_agent` function imports `GoogleModel` and `GoogleProvider` inside the function scope. These should be moved to the top of the file for better readability and consistency.
- **Location**: `src/egregora/agents/taxonomy.py:43`
- **Context**: Function-level imports can hide dependencies and are generally discouraged in favor of top-level imports.
- **Suggested Persona**: refactor

### 2. Add docstrings to Pydantic models
- **Description**: The Pydantic models (`ClusterInput`, `ClusterTags`, `GlobalTaxonomyResult`) have class-level docstrings but the fields themselves lack specific documentation. Adding docstrings to each field would improve clarity for developers.
- **Location**: `src/egregora/agents/taxonomy.py:13`
- **Context**: Clear documentation for data models is crucial for maintainability, especially for code that interacts with LLM APIs where the structure is critical.
- **Suggested Persona**: shepherd

### 3. Refactor brittle model name prefix stripping
- **Description**: The code uses `model_name.removeprefix("google-gla:")` to manipulate the model name before passing it to the `GoogleModel` constructor. This is brittle as it assumes a specific prefix and couples the agent code to a specific naming convention.
- **Location**: `src/egregora/agents/taxonomy.py:48`
- **Context**: This hardcoded string manipulation makes the code less flexible. A better approach might involve a dedicated utility function or a more robust way of handling model names.
- **Suggested Persona**: refactor
