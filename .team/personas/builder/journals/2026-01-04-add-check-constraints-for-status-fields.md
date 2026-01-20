# Builder Journal: Add CHECK Constraints for Status Fields

**Date**: 2026-01-04
**Persona**: Builder (Data Architect)
**Task**: Add database-level CHECK constraints for enum-like status fields

## Problem Statement

The `posts` and `tasks` tables had `status` columns defined as plain VARCHAR with no database-level validation. This allowed invalid status values to be inserted, potentially causing:
- Data integrity issues (e.g., "PUBLISHED" vs "published")
- Application logic bugs (unexpected status values)
- Difficult debugging (where did this invalid status come from?)

## Business Rules Identified

### Posts Table
Valid status values: `draft`, `published`, `archived`

### Tasks Table
Valid status values: `pending`, `processing`, `completed`, `failed`, `superseded`

## Implementation Approach: TDD

### Phase 1: DESIGN
- Analyzed schema definitions in `src/egregora/database/schemas.py`
- Identified missing CHECK constraints for status fields
- Reviewed DuckDB documentation on constraint support

### Phase 2: RED - Write Failing Tests
Created `tests/unit/database/test_schema_constraints.py` with 4 test cases:
1. `test_posts_status_check_constraint_allows_valid_values` - Verify valid statuses accepted
2. `test_posts_status_check_constraint_rejects_invalid_values` - Verify invalid statuses rejected
3. `test_tasks_status_check_constraint_allows_valid_values` - Same for tasks
4. `test_tasks_status_check_constraint_rejects_invalid_values` - Same for tasks

Initial test run: All 4 tests failed (expected) because constraints didn't exist yet.

### Phase 3: GREEN - Implement Constraints

**Discovery: DuckDB Limitation**
Attempted to use `ALTER TABLE ADD CONSTRAINT CHECK` but discovered DuckDB doesn't support this:
```
Not implemented Error: No support for that ALTER TABLE option yet!
```

**Solution: Include Constraints in CREATE TABLE**
Modified `create_table_if_not_exists()` to accept `check_constraints` parameter:
```python
def create_table_if_not_exists(
    conn: Any,
    table_name: str,
    schema: ibis.Schema,
    *,
    overwrite: bool = False,
    check_constraints: dict[str, str] | None = None,
) -> None:
```

**Created Helper Function**
```python
def get_table_check_constraints(table_name: str) -> dict[str, str]:
    """Get CHECK constraints for a table based on business logic."""
    if table_name == "posts":
        valid_values = ", ".join(f"'{status}'" for status in VALID_POST_STATUSES)
        return {"chk_posts_status": f"status IN ({valid_values})"}
    elif table_name == "tasks":
        valid_values = ", ".join(f"'{status}'" for status in VALID_TASK_STATUSES)
        return {"chk_tasks_status": f"status IN ({valid_values})"}
    return {}
```

**Added Constants**
```python
VALID_POST_STATUSES = ("draft", "published", "archived")
VALID_TASK_STATUSES = ("pending", "processing", "completed", "failed", "superseded")
```

### Phase 4: VERIFY - Test and Validate

- **Constraint tests**: All 4 tests passed ✅
- **Full test suite**: 843 tests passed, 3 skipped ✅
- **No regressions**: Existing functionality maintained ✅

## Files Modified

1. `src/egregora/database/schemas.py`:
   - Added `check_constraints` parameter to `create_table_if_not_exists()`
   - Created `get_table_check_constraints()` function
   - Added VALID_POST_STATUSES and VALID_TASK_STATUSES constants
   - Deprecated `apply_table_constraints()` with clear documentation

2. `tests/unit/database/test_schema_constraints.py`:
   - New file with comprehensive constraint testing
   - 4 test methods covering valid and invalid cases
   - Uses pytest fixtures for clean database setup

## Key Lessons

### 1. Database Feature Limitations
Always check database-specific limitations before implementing. DuckDB's lack of ALTER TABLE ADD CONSTRAINT CHECK required a different approach than traditional databases.

### 2. Centralized Business Rules
The `get_table_check_constraints()` function centralizes business rules, making it easy to:
- See all valid values in one place
- Update constraints when business rules change
- Apply constraints consistently across the codebase

### 3. Test-Driven Approach
Writing tests first helped:
- Clarify expected behavior (what should pass/fail)
- Discover implementation challenges early
- Ensure constraints actually work as intended

## Impact

- **Data Integrity**: Invalid status values now rejected at database level
- **Type Safety**: Business rules enforced by database, not just application code
- **Maintainability**: Centralized constraint definitions in `get_table_check_constraints()`
- **Test Coverage**: 4 new tests covering constraint behavior

## Future Considerations

1. **Migration Strategy**: Existing databases need migration to add constraints
2. **Other Enum Fields**: Consider CHECK constraints for other enum-like columns
3. **Performance**: CHECK constraints have minimal overhead but should be benchmarked for high-volume inserts
4. **Documentation**: Update schema documentation to reflect constraint requirements

---

**Builder's Note**: This work demonstrates the value of database-level constraints for maintaining data integrity. While application-level validation is important, database constraints provide a critical safety net that prevents invalid data from ever being persisted.
