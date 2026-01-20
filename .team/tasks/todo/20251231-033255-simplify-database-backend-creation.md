---
id: 20251231-033255-simplify-database-backend-creation
status: todo
title: "Simplify database backend creation"
created_at: "2025-12-31T03:32:55Z"
target_module: "src/egregora/orchestration/pipelines/write.py"
assigned_persona: "refactor"
---

## Description

The `_create_database_backends` function in `src/egregora/orchestration/pipelines/write.py` contains a nested helper function `_validate_and_connect`, which increases its complexity and reduces readability. This structure makes the logic harder to follow and test independently.

## Task

Refactor the function by:
1.  **Extracting the Helper:** Move the `_validate_and_connect` logic into a standalone private function within the module.
2.  **Improving Structure:** Simplify the main `_create_database_backends` function to call the new helper, making the flow more direct and easier to understand.
3.  **Enhancing Clarity:** Ensure the new function has a clear name and docstring that explains its purpose.

## Code Snippet

```python
# TODO: [Taskmaster] Simplify database backend creation
def _create_database_backends(
    site_root: Path,
    config: EgregoraConfig,
) -> tuple[str, any, any]:
    """Create database backends for pipeline and runs tracking."""

    def _validate_and_connect(value: str, setting_name: str) -> tuple[str, any]:
        if not value:
            msg = f"Database setting '{setting_name}' must be a non-empty connection URI."
            raise ValueError(msg)

        parsed = urlparse(value)
        if not parsed.scheme:
            msg = (
                "Database setting '{setting}' must be provided as an Ibis-compatible connection "
                "URI (e.g. 'duckdb:///absolute/path/to/file.duckdb' or 'postgres://user:pass@host/db')."
            )
            raise ValueError(msg.format(setting=setting_name))

        if len(parsed.scheme) == 1 and value[1:3] in {":/", ":\\"}:
            msg = (
                "Database setting '{setting}' looks like a filesystem path. Provide a full connection "
                "URI instead (see the database settings documentation)."
            )
            raise ValueError(msg.format(setting=setting_name))

        normalized_value = resolve_db_uri(value, site_root)
        return normalized_value, ibis.connect(normalized_value)

    runtime_db_uri, pipeline_backend = _validate_and_connect(
        config.database.pipeline_db, "database.pipeline_db"
    )
    _runs_db_uri, runs_backend = _validate_and_connect(config.database.runs_db, "database.runs_db")

    return runtime_db_uri, pipeline_backend, runs_backend
```
