# Archive Lifecycle Management

This guide describes how database snapshots are prepared, uploaded and eventually pruned.

1. **Export & Compress** – `archive_db.py` exports the DuckDB, CSV tables and metadata then creates a compressed tarball.
2. **Upload** – The compressed snapshot is uploaded to the Internet Archive with a version number and descriptive metadata.
3. **Verification** – Upload success is verified and a record is stored locally in `archived_databases`.
4. **Retention Enforcement** – During each archive run, older items that exceed the [retention policy](archive_retention_policy.md) are removed.
5. **Status Reporting** – Run `causaganha archive-status` to view sync details and the latest snapshot versions.
