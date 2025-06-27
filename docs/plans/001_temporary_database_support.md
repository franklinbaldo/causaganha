# Plan: Support for Temporary Databases in CausaGanhaDB

**Date:** 2025-06-27
**Author:** Jules (AI Assistant)
**Status:** Implemented (on branch `feat/temp-duckdb`)

## 1. Executive Summary

This document outlines the rationale and implementation details for adding support for temporary (file-backed) databases within the `CausaGanhaDB` class. This enhancement allows `CausaGanhaDB` to be instantiated without requiring a pre-defined database file path, defaulting to a temporary file that is automatically managed and cleaned up. This increases flexibility, simplifies usage in ephemeral environments (like testing or short-lived scripts), and reduces the need for manual file management by users in such scenarios.

## 2. Background and Rationale

Previously, `CausaGanhaDB` required a specific file path for the DuckDB database to be provided upon instantiation (defaulting to `data/causaganha.duckdb`). While suitable for persistent storage, this had limitations:

*   **Testing:** Required manual setup and teardown of database files for isolated test runs, or careful management of a shared test database.
*   **Ephemeral Use Cases:** For scripts or processes that needed a database only for their runtime duration, users still had to define a path, and potentially manage cleanup.
*   **Simplicity:** For new users or quick tasks, the need to specify a path and ensure the directory exists could be a small barrier.

Introducing temporary database support addresses these points by:

*   Providing a "zero-configuration" mode for database usage.
*   Ensuring automatic cleanup of database files created for temporary use.
*   Simplifying test fixtures and reducing boilerplate for database setup in tests.

## 3. Goals

*   Allow `CausaGanhaDB` to be instantiated without a `db_path` argument.
*   When no `db_path` is provided, use a file-backed temporary DuckDB database.
*   Ensure the temporary database file is automatically deleted when the `CausaGanhaDB` instance is closed.
*   Maintain existing functionality for persistent databases when a `db_path` is provided.
*   Ensure database migrations run correctly for both temporary and persistent databases.
*   Minimize impact on existing code that uses `CausaGanhaDB`.

## 4. Implemented Solution (Relative to previous HEAD)

The following key changes were implemented in the `feat/temp-duckdb` branch:

### 4.1. `CausaGanhaDB` Class Modifications (`src/database.py`)

*   **Constructor (`__init__`)**:
    *   The `db_path` parameter was changed from `Path = Path("data/causaganha.duckdb")` to `Optional[Path] = None`.
    *   New instance variables `self._temp_db_file_path: Optional[Path]` and `self._temp_db_file_obj: Optional[tempfile.NamedTemporaryFile]` were added to manage the temporary file. (Note: `_temp_db_file_obj` is no longer used to keep the file open after initial name generation, path is stored in `_temp_db_file_path`).

*   **Connection Logic (`connect` method)**:
    *   If `self.db_path` is `None` (i.e., no path provided to constructor):
        1.  A unique temporary file name with a `.duckdb` suffix is generated using `tempfile.NamedTemporaryFile(delete=True)`. The file is immediately deleted by `NamedTemporaryFile` itself (or on closing the temporary handle), ensuring only the name is used.
        2.  This path is stored in `self._temp_db_file_path` and also assigned to `self.db_path` for the current instance's lifecycle.
        3.  DuckDB connects to this path. Since the file does not exist at this point, DuckDB creates and initializes it.
    *   If `self.db_path` *is* provided:
        1.  A check is performed: if the `db_path` points to an existing file that is empty (0 bytes), that empty file is deleted. This prevents DuckDB IOErrors when it tries to open an existing but uninitialized (empty) file.
    *   The `duckdb.connect()` call then proceeds with the determined path (either the provided one or the temporary one).
    *   The `_run_migrations()` method is called as before.

*   **Cleanup Logic (`close` method)**:
    *   The existing database connection (`self.conn`) is closed.
    *   If `self._temp_db_file_path` is set (meaning a temporary database was used):
        1.  The file at `self._temp_db_file_path` is deleted using `self._temp_db_file_path.unlink(missing_ok=True)`.
        2.  `self._temp_db_file_path` is reset to `None`.

*   **Migration Path (`_run_migrations` method)**:
    *   The path to the migrations directory was corrected from `Path(__file__).parent.parent.parent / "migrations"` to `Path(__file__).resolve().parent.parent / "migrations"`. This ensures it correctly locates the `migrations/` directory relative to the project root, regardless of where `CausaGanhaDB` is instantiated or run from.

### 4.2. Testing (`tests/test_database.py`)

*   A new test file `tests/test_database.py` was created to specifically test `CausaGanhaDB`.
*   **Test Cases Added**:
    *   `test_temp_db_creation_and_cleanup`: Verifies that instantiating `CausaGanhaDB()` without arguments results in a temporary database being created, migrations run, and the file is cleaned up on `close()`.
    *   `test_persistent_db_creation`: Verifies that providing a `db_path` creates a persistent database, migrations run, and the file remains until manually handled (as per test logic). It also covers the scenario where an empty file at `db_path` is correctly handled.
    *   `test_db_info_with_temp_db`: Checks `get_db_info()` output for temporary databases.
    *   `test_db_info_with_persistent_db`: Checks `get_db_info()` output for persistent databases.
*   These tests ensure that core database operations (connection, migration, basic queries) function correctly for both modes.

### 4.3. Dependencies and Environment

*   Ensured `duckdb` and other necessary dependencies are installed (using `uv pip install .` within a virtual environment).

### 4.4. `.gitignore`
*   Added `build/` and `dist/` to `.gitignore` to prevent build artifacts from being committed.

## 5. Impact

*   **Developer Experience:** Simplifies database setup for testing and small scripts.
*   **Testing:** Allows for cleaner, more isolated tests without manual DB file management.
*   **Flexibility:** `CausaGanhaDB` can now be used in a wider range of scenarios without code modification.
*   **Backward Compatibility:** Existing code that provides a `db_path` will continue to function as before. The default path if `db_path` is explicitly specified (e.g. in `config.py` if it instantiates `CausaGanhaDB`) remains unchanged unless that instantiation point is modified to pass `None`.

## 6. Future Considerations (Optional)

*   **In-Memory Option:** Consider adding an explicit option for a true in-memory DuckDB database (`:memory:`) if file-system access is undesirable even for temporary files in some contexts. However, file-backed temporary databases are often preferred for debugging and because some DuckDB extensions or features might behave differently with pure in-memory vs. file-backed databases.
*   **Configuration:** Review if the default behavior (temporary vs. persistent) should be configurable via an environment variable or a global setting, though the current explicit-path-for-persistent, no-path-for-temporary seems a reasonable default.

This implementation provides a significant improvement in the usability and flexibility of `CausaGanhaDB`.
