# Development

This guide provides instructions for setting up a development environment, running tests, and contributing to the CausaGanha project.

## Development Workflow

1.  **Set up the Environment**: Follow the [Getting Started](getting-started.md) guide to clone the repository and install dependencies with `uv sync --dev`.

2.  **Make Code Changes**: Implement your feature or bug fix. Ensure all new code follows the existing style and architectural patterns.

3.  **Run Linters and Formatters**: Before committing, it's a good practice to run `ruff` to ensure your code is clean and consistent.

    ```bash
    # Auto-format the code
    uv run ruff format

    # Check for linting errors and auto-fix where possible
    uv run ruff check --fix
    ```

4.  **Run Tests**: Make sure all existing tests pass and, if necessary, add new tests to cover your changes.

    ```bash
    uv run pytest -q
    ```

## Testing

The project uses `pytest` for testing. Tests are located in the `tests/` directory and are separated into `unit` and `integration` tests.

-   **Unit Tests**: Test individual components in isolation, often using mocks for external dependencies.
-   **Integration Tests**: Test the interaction between multiple components, such as the pipeline and the database.

To run the full test suite:
```bash
uv run pytest
```

To run with coverage reporting:
```bash
uv run pytest --cov=causaganha
```

## Building Documentation

The documentation is built with MkDocs and the Material for MkDocs theme.

1.  **Serve Locally**: To preview your changes as you work, you can serve the documentation locally. The site will automatically reload when you save a file.

    ```bash
    uv run mkdocs serve
    ```

2.  **Build Statically**: To generate the static HTML site, which is what the CI does, run the build command.

    ```bash
    uv run mkdocs build
    ```

    The `--strict` flag is used in the CI to treat warnings as errors, ensuring the documentation is always in a a clean state.
