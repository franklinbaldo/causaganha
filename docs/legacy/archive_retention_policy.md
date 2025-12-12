# CausaGanha Archive Retention Policy

This document defines how long database snapshots and supporting artifacts are kept in the Internet Archive.

## Policy Overview

- **Weekly snapshots** are retained for **6 months**.
- **Monthly snapshots** are retained for **5 years**.
- **Quarterly or major release snapshots** are retained **indefinitely**.
- Snapshot metadata includes a version number and upload timestamp for traceability.

Older items are pruned automatically by the archiving scripts once their retention period expires.
