---
id: 20260104-013449-taskmaster-aggregate
status: todo
title: "Taskmaster Run: src/egregora/agents/enricher.py"
created_at: "2026-01-04T01:34:49+00:00"
target_module: "src/egregora/agents/enricher.py"
assigned_persona: "taskmaster"
---

## Summary

A systematic review of `src/egregora/agents/enricher.py` revealed significant technical debt. The module is overly complex, monolithic, and contains several code smells, including brittle logic, hardcoded values, duplicated code, and a potential security vulnerability. Refactoring these areas will improve maintainability, robustness, and security.

## Identified Tasks

### 1. Externalize Hardcoded Configuration Values
- **Description**: The module contains hardcoded configuration values like `HEARTBEAT_INTERVAL`. These should be moved to the application's configuration settings to improve flexibility.
- **Location**: `src/egregora/agents/enricher.py:72`
- **Context**: Hardcoding configuration makes it difficult to adjust application behavior without changing the code, complicating deployment and testing.
- **Suggested Persona**: refactor

### 2. Refactor Brittle Data Conversion Logic
- **Description**: The `_frame_to_records` function uses a fragile multi-level `try-except` block to handle different data frame types. This should be refactored to rely on a standardized data format.
- **Location**: `src/egregora/agents/enricher.py:234`
- **Context**: This brittle logic can easily break if an upstream data source changes its output format, leading to runtime errors. Standardizing the data interchange format would make the pipeline more robust.
- **Suggested Persona**: refactor

### 3. Refactor Duplicated Enrichment Check Logic
- **Description**: The `_enqueue_url_enrichments` and `_enqueue_media_enrichments` functions contain duplicated logic for checking if an item has already been enriched. This logic should be extracted into a shared helper function.
- **Location**: `src/egregora/agents/enricher.py:318`
- **Context**: Code duplication increases the maintenance burden and the risk of introducing inconsistencies. A single, shared function would be easier to maintain and ensure consistent behavior.
- **Suggested Persona**: refactor

### 4. Decompose Monolithic EnrichmentWorker Class
- **Description**: The `EnrichmentWorker` class is a monolithic component responsible for task fetching, URL and media enrichment, file staging, and result persistence. It should be broken down into smaller, more focused classes.
- **Location**: `src/egregora/agents/enricher.py:468`
- **Context**: This class violates the Single Responsibility Principle, making it difficult to understand, test, and maintain. Decomposing it would lead to a cleaner, more modular design.
- **Suggested Persona**: refactor

### 5. Simplify Complex Async-in-Sync Wrapper
- **Description**: The `_enrich_single_url` method uses a complex and error-prone pattern to run an asynchronous agent from a synchronous context by manually managing an asyncio event loop.
- **Location**: `src/egregora/agents/enricher.py:587`
- **Context**: This "async-in-sync" pattern is an architectural smell that complicates the codebase and can lead to subtle bugs. The overall concurrency model should be revisited to avoid this.
- **Suggested Persona**: refactor

### 6. Decompose Complex Batch Execution Method
- **Description**: The `_execute_url_single_call` method is long and handles multiple concerns, including prompt rendering, model/key rotation, API calls, and response parsing. It should be broken down into smaller helper functions.
- **Location**: `src/egregora/agents/enricher.py:780`
- **Context**: Large, complex methods are difficult to read, test, and debug. Decomposing this method would improve code clarity and maintainability.
- **Suggested Persona**: refactor

### 7. Simplify Complex File Staging Logic
- **Description**: The `_stage_file` function contains complex logic for managing a ZIP file handle to extract and stage media files. This logic is error-prone and could be simplified.
- **Location**: `src/egregora/agents/enricher.py:1029`
- **Context**: Direct management of file I/O and ZIP archives can lead to resource leaks and hard-to-debug errors. Encapsulating this logic in a dedicated utility could improve robustness.
- **Suggested Persona**: refactor

### 8. Refactor to Use Parameterized Queries
- **Description**: The `_persist_media_results` function uses an f-string to construct a SQL query, creating a potential SQL injection vulnerability. The query should be rewritten using parameterized statements.
- **Location**: `src/egregora/agents/enricher.py:1503`
- **Context**: Constructing SQL queries with string formatting is a major security risk. Using parameterized queries is a standard practice to prevent SQL injection attacks.
- **Suggested Persona**: security

### 9. Improve Brittle JSON Parsing from LLM Output
- **Description**: The `_parse_media_result` function uses string manipulation to clean up JSON returned by an LLM before parsing. This is brittle and can easily break.
- **Location**: `src/egregora/agents/enricher.py:1528`
- **Context**: LLM output can be unpredictable. Relying on simple string stripping is not a robust parsing strategy. A more resilient approach, perhaps with more sophisticated validation, is needed.
- **Suggested Persona**: refactor
