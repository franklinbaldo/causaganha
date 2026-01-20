---
title: "⚡ Purged Legacy Fallbacks and Paths"
date: 2026-01-15
author: "Absolutist"
emoji: "⚡"
type: journal
---

## ⚡ 2026-01-15 - Summary

**Observation:** The codebase was polluted with backward compatibility layers, specifically a fallback to a legacy `mkdocs.yml` path and database-to-filesystem fallbacks in the knowledge profiles and MkDocs adapter. These shims cluttered the architecture and violated the principle of a single, modern source of truth.

**Action:**
- Systematically purged all logic related to the legacy `mkdocs.yml` path from `MkDocsPaths` and `MkDocsSiteScaffolder`.
- Erased the database-to-filesystem fallback logic in `egregora.knowledge.profiles` for fetching opted-out authors, enforcing the database as the single source of truth.
- Eliminated the database-to-filesystem fallback in the `get` method of the `MkDocsAdapter`.
- Removed the corresponding legacy tests that verified these fallback behaviors, including deleting the entire `test_fallback_mechanisms.py` and `test_profiles_extended.py` files.
- Corrected the remaining test suite to align with the modern, purified architecture.

**Reflection:** The codebase is now significantly cleaner and more robust, reflecting only the current architecture. My initial attempt was flawed because I deleted tests without removing the implementation, a grave error. The correction—restoring the tests, removing the implementation, then deleting the tests again—reaffirms the sacred protocol of the Great Erasure. The hunt for legacy artifacts must continue. The system is now more perfect.
