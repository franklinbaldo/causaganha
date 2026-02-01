---
title: "🔨 Improve Type Safety in Pipeline Context"
date: 2026-01-04
author: "Artisan"
emoji: "🔨"
type: journal
focus: "Typing"
---

# Artisan Improvement 🔨

## Focus
**Typing** - Replace loose `Any` type with precise `InputAdapter` protocol

## Before
```python
# src/egregora/orchestration/context.py
from typing import TYPE_CHECKING, Any

@dataclass(slots=True)
class PipelineState:
    adapter: Any = None  # InputAdapter protocol
    ...

class PipelineContext:
    @property
    def adapter(self) -> Any:
        return self.state.adapter

    def with_adapter(self, adapter: Any) -> PipelineContext:
        """Update adapter in state."""
        ...
```

**Issues:**
- `Any` type provides no type safety
- IDE cannot provide autocomplete for adapter methods
- MyPy cannot catch type errors (e.g., passing wrong adapter type)
- Comment says "InputAdapter protocol" but type is `Any`
- No documentation on method parameters

## After
```python
# src/egregora/orchestration/context.py
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from egregora.input_adapters.base import InputAdapter
    ...

@dataclass(slots=True)
class PipelineState:
    adapter: InputAdapter | None = None  # InputAdapter instance for source-specific parsing
    ...

class PipelineContext:
    @property
    def adapter(self) -> InputAdapter | None:
        return self.state.adapter

    def with_adapter(self, adapter: InputAdapter) -> PipelineContext:
        """Update adapter in state.

        Args:
            adapter: InputAdapter instance for source-specific parsing

        Returns:
            Self for method chaining

        """
        ...
```

**Improvements:**
- ✅ Type-safe: MyPy can now verify adapter is correct type
- ✅ IDE autocomplete: Shows `source_name`, `parse()`, `deliver_media()` methods
- ✅ Self-documenting: Type annotation replaces vague comment
- ✅ Added docstring with Args/Returns sections (Google style)
- ✅ Preserved `library: Any` (intentional - avoids V2→V3 circular import)

## Why
**Developer Experience:**
- Catch type errors at development time, not runtime
- IDE autocomplete improves discoverability of adapter API
- Self-documenting code reduces need for external documentation

**Type Safety:**
- Prevents accidentally passing wrong types (e.g., `str`, `dict`, wrong adapter)
- MyPy can verify all call sites use correct adapter types
- Future refactorings are safer (compiler catches broken code)

## Testing Approach
Followed TDD (Test-Driven Development):

1. **🔴 RED**: Wrote behavioral tests first
   - Created `tests/unit/orchestration/test_context.py`
   - Test 1: Accepts `InputAdapter` instance
   - Test 2: Accepts `None` for lazy initialization
   - Verified tests pass with current `Any` type (baseline)

2. **🟢 GREEN**: Applied refactoring
   - Replaced `Any` with `InputAdapter | None`
   - Added import in `TYPE_CHECKING` block
   - Added docstring with Args/Returns

3. **🔵 REFACTOR**: Verified correctness
   - Tests still pass (behavior unchanged)
   - MyPy shows no errors for `context.py`
   - Full unit test suite passes

## Impact
- **Files changed**: 2
  - `src/egregora/orchestration/context.py` (4 locations)
  - `tests/unit/orchestration/test_context.py` (new file, 2 tests)
- **Lines changed**: ~15
- **Type safety**: Improved from `Any` → `InputAdapter | None`
- **Breaking changes**: None (behavioral compatibility preserved)

## Lessons Learned
- Using `TYPE_CHECKING` block avoids runtime circular imports while enabling type hints
- TDD for refactoring ensures behavior preservation
- Small, incremental type improvements are better than "big bang" type safety rewrites
- Comments like "# InputAdapter protocol" are code smells → use actual types instead
