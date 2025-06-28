# Distributed Architecture Decisions

CausaGanha operates with a two-tier architecture:

1. **Local DuckDB** used by the async pipeline and CLI tools.
2. **Internet Archive Storage** for sharing the database across all environments.

Key decisions:

- The database is synchronized using `ia_database_sync.py` which relies on the finalized lock protocol (see `distributed_lock_protocol.md`).
- GitHub Actions jobs run one at a time for database operations, minimizing concurrent writes.
- The system prefers local changes when hashes differ, but downloads from IA if the remote file is newer.
- Locks include metadata for debugging and automatic stale cleanup.

These decisions keep the distributed setup simple while allowing multiple developers to collaborate without a dedicated server.
