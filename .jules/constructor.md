## 2024-05-23 - [Storage] Context: Implementing the persistence layer for gathered legal data.
Strategy: Using Ibis with DuckDB. Implementing `store_intimations` using `asyncio.to_thread` for async wrapper compliance.
Changes: `tests/unit/test_storage.py`, `src/causaganha/storage/schema.py`, `src/causaganha/storage/queries.py`
