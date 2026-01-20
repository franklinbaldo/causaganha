---
title: "💎 Simplify DuckDB Repository"
date: "2025-12-25"
author: "Essentialist"
emoji: "💎"
type: journal
---

## 💎 2025-12-25 - Simplify DuckDB Repository
**Observation:** The `DuckDBDocumentRepository` had complex, multi-path logic for initialization, saving, and deleting, with fallbacks for connections that didn't support raw SQL. This violated the "One good path" and "Explicit over implicit" heuristics. It also had duplicated `save` and `save_entry` methods.
**Action:** I refactored the repository to enforce a single, reliable path by requiring a raw SQL connection (`.con`). This allowed me to remove all fallback logic, `try...except` blocks, and dead code. I consolidated the `save` and `save_entry` methods into a single polymorphic `save` method. The entire process was guided by strict TDD.
**Reflection:** The `DuckDBDocumentRepository` is now much simpler and more robust. However, the `get_entries_by_source` method still relies on a raw SQL query for JSON extraction. While this is currently the most reliable approach, it would be beneficial to investigate if future versions of the Ibis library provide a more elegant, cross-backend way to handle this, which would further align with the "Interfaces over implementations" heuristic. Additionally, the `knowledge` directory was not explored and might contain complex logic that could be simplified.
