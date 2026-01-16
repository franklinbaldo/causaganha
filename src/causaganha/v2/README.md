# CausaGanha V2 Core

This directory contains the V2 implementation of the CausaGanha architecture.

## Architecture

The V2 architecture is designed for modularity, scalability, and type safety, leveraging modern Python libraries.

### Components

*   **`api/`**: **Data Collection**.
    *   `client.py`: Async client for PJe Communications API using `httpx`.
    *   Handles pagination and authentication automatically.

*   **`storage/`**: **Data Persistence**.
    *   `connection.py`: Manages DuckDB connection (Singleton pattern).
    *   `queries.py`: Ibis-based queries for storing and retrieving data.
    *   Ensures strict schema validation and safe SQL execution.

*   **`analysis/`**: **AI Analysis**.
    *   `analyzer.py`: Uses `pydantic-ai` (wrapping LLMs like Gemini) to analyze legal decisions.
    *   `models.py`: Strict Pydantic models for structured output (e.g., `DecisionAnalysis`).

*   **`pipeline/`**: **Orchestration**.
    *   `collect.py`: Orchestrates fetching data from API and storing it.
    *   `analyze.py`: Batches unanalyzed records and sends them to the Analyzer.
    *   `score.py`: Updates lawyer ratings using OpenSkill.

*   **`utils/`**: Shared utilities.

## Usage

Most operations are orchestrated via the main CLI (in `src/causaganha/cli.py`) or Cloud Functions.

### Running Tests

```bash
uv run pytest tests/v2/
```

### Dependency Management

All dependencies are managed via `pyproject.toml` and `uv`.
