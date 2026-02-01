---
title: "Fix Blocker: Demo Generation Fails on Date Parsing"
date: 2024-07-29
author: "Curator"
emoji: "🎭"
type: task
tags:
  - "#blocker"
  - "#bug"
  - "#ux"
  - "#forge"
status: "todo"
priority: "high"
---

## 🛑 Blocker: `egregora demo` command is failing

**Persona:** Forge 🛠️

### Description

The Curation Cycle is currently blocked because the `egregora demo` command fails during execution. This prevents any evaluation of the generated MkDocs blog.

### The Error

The command fails with a `RuntimeError` due to an inability to parse a date string.

**Error Message:**
```
RuntimeError: Failed to persist post document: Failed to parse date string for
frontmatter: '2025-10-28 14:10 to 14:15'. Original error: Failed to parse
datetime from '2025-10-28 14:10 to 14:15': Unknown string format: 2025-10-28
14:10 to 14:15
```

**Relevant Traceback Section:**
```python
│ /app/src/egregora/agents/tools/writer_tools.py:176 in write_post_impl        │
│                                                                              │
│   173 │   except Exception as exc:                                           │
│   174 │   │   msg = f"Failed to persist post document: {exc}"                │
│   175 │   │   logger.exception(msg)                                          │
│ ❱ 176 │   │   raise RuntimeError(msg) from exc                               │
```

### Why It Matters

This is a **critical blocker** for the Curator persona. No UX/UI evaluation or improvement work can proceed until the demo site can be successfully generated.

### What to Do

1.  **Investigate:** Trace the origin of the invalid date string `'2025-10-28 14:10 to 14:15'`. It appears to be coming from the data used by the writer agent when creating post frontmatter.
2.  **Fix:** Implement a fix in the data processing or parsing logic to handle this date range format. The system should probably use the start time (`2025-10-28 14:10`) as the canonical date for the post.
3.  **Verify:** The fix is successful when the `uv run egregora demo` command completes without any errors.

### Where to Look

-   `src/egregora/agents/tools/writer_tools.py`: The error originates here.
-   The data generation/fixture logic for the `demo` command. It's likely using sample data that includes this date range format.
