# Distributed Lock Protocol

The CausaGanha platform relies on a simple sentinel file lock stored on the Internet Archive to coordinate database access across multiple environments (developer machines and GitHub Actions). This document finalizes the lock protocol design used by `ia_database_sync.py`.

## Lock Acquisition

1. A worker requests a lock by uploading a small JSON file to the IA item `causaganha-database-lock`.
2. The JSON payload contains:
   - `operation`: upload or download
   - `created_at`: ISO timestamp
   - `created_by`: user or CI host
   - `hostname`: machine hostname
   - `timeout_minutes`: how long the lock is valid
   - `expires_at`: epoch timestamp when the lock should be considered stale
3. If the upload succeeds, the worker proceeds with database operations.

## Lock Release

1. After completing the operation the worker deletes `causaganha-database-lock` using `ia delete`.
2. On failure or interruption the lock may remain. The sync script checks the `expires_at` field and cleans stale locks automatically after the timeout.

## Failure Handling

- Workers waiting for a lock poll every 30 seconds and respect a configurable timeout.
- If the lock expires while waiting, the stale file is removed and the operation continues.
- Manual cleanup can be performed with `ia delete causaganha-database-lock` if necessary.

This protocol keeps coordination simple while providing enough metadata to troubleshoot issues.
