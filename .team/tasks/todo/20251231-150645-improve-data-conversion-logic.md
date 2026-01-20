---
id: 20251231-150645-improve-data-conversion-logic
status: todo
title: "Improve Brittle Data Conversion Logic"
created_at: "2025-12-31T15:06:45Z"
target_module: "src/egregora/orchestration/runner.py"
assigned_persona: "refactor"
---

## 📋 Improve Brittle Data Conversion Logic

**Context:**
The logic in `_process_single_window` for converting the `enriched_table` to a list of messages is brittle. It uses a series of nested `try-except` blocks to handle different possible data types, which is a sign of a fragile design. This approach can hide underlying issues and makes the code difficult to reason about.

A more robust solution would be to establish a clearer contract for the data type of `enriched_table` or to create a dedicated utility function that handles the conversion in a more predictable and type-safe manner.

**Task:**
1.  Analyze the different data types that `enriched_table` can be.
2.  Design and implement a more robust data conversion mechanism. This could be a dedicated function or a class that encapsulates the conversion logic.
3.  Replace the existing `try-except` blocks with a call to the new conversion mechanism.
4.  Ensure that the new implementation is well-tested.

**Code Snippet:**
```python
# TODO: [Taskmaster] Improve brittle data conversion logic.
# Convert table to list for command processing
try:
    messages_list = enriched_table.execute().to_pylist()
except (AttributeError, TypeError):
    try:
        messages_list = enriched_table.to_pylist()
    except (AttributeError, TypeError):
        messages_list = enriched_table if isinstance(enriched_table, list) else []
```

**Acceptance Criteria:**
- The nested `try-except` blocks for data conversion are removed.
- A new, more robust conversion mechanism is in place.
- The application correctly processes data without any regressions.
