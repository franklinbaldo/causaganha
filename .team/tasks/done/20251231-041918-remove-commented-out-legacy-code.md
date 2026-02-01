---
id: ${TIMESTAMP}-remove-commented-out-legacy-code
status: todo
title: "Chore: Remove Commented-Out Legacy Code"
created_at: "${ISO_TIMESTAMP}"
target_module: "src/egregora/orchestration/pipelines/write.py"
assigned_persona: "absolutist"
---

## 📋 Chore: Remove Commented-Out Legacy Code

**Description:**
The file `src/egregora/orchestration/pipelines/write.py` contains numerous large blocks of commented-out code. These are remnants of previous refactoring efforts and are no longer needed.

**Context:**
This dead code clutters the file, making it harder to read and navigate. Removing it will improve the overall code quality and maintainability without affecting functionality. Version control history can be used to retrieve the old code if ever needed.

**Example Snippet of Commented-out Code:**
```python
# _process_background_tasks REMOVED - functionality moved to PipelineRunner

# _process_single_window REMOVED - functionality moved to PipelineRunner

# _process_window_with_auto_split REMOVED - functionality moved to PipelineRunner

# _warn_if_window_too_small REMOVED - functionality moved to PipelineRunner

# _ensure_split_depth REMOVED - functionality moved to PipelineRunner

# _split_window_for_retry REMOVED - functionality moved to PipelineRunner

# _resolve_context_token_limit REMOVED - functionality moved to PipelineRunner
```
