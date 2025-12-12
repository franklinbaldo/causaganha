# Constructor's Journal

## 2024-05-22 - [Storage Layer]
**Context:** Implementing the Ibis storage layer for CausaGanha V2. The goal is to store `Intimation` objects fetched from the API into DuckDB.
**Strategy:**
- Use Ibis for all database interactions.
- Implement a singleton pattern for `get_connection` to avoid DuckDB lock contention.
- Define the schema for `intimations` table.
- Implement `store_intimations` query using `memtable` or `insert`.
**Changes:**
- `tests/unit/test_storage.py`
- `src/causaganha/storage/connection.py`
- `src/causaganha/storage/schema.py`
- `src/causaganha/storage/queries.py`
