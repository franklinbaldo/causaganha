---
id: 20251231-041850-refactor-cli-validation-logic
status: todo
title: "Refactor: Extract Validation Logic from run_cli_flow"
created_at: "2025-12-31T04:18:50Z"
target_module: "src/egregora/orchestration/pipelines/write.py"
assigned_persona: "artisan"
---

## 📋 Refactor: Extract Validation Logic from run_cli_flow

**Description:**
The  function in  currently handles multiple validation tasks directly within its body, including parsing dates, validating timezones, and checking for a valid API key. This makes the function overly long and difficult to read.

**Context:**
Extracting the validation logic into separate, well-named functions will improve the readability and maintainability of . Each new function will have a single responsibility, making the code easier to understand, test, and debug.

**Code Snippet:**
```python
# TODO: [Taskmaster] Refactor validation logic into separate functions
def run_cli_flow(
    input_file: Path,
    *,
    output: Path = Path("site"),
    # ... many other parameters
) -> None:
    """Execute the write flow from CLI arguments."""
    # ...
    if from_date:
        try:
            from_date_obj = parse_date_arg(from_date, "from_date")
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            raise SystemExit(1) from e
    if to_date:
        try:
            to_date_obj = parse_date_arg(to_date, "to_date")
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            raise SystemExit(1) from e

    if timezone:
        try:
            validate_timezone(timezone)
            console.print(f"[green]Using timezone: {timezone}[/green]")
        except ValueError as e:
            console.print(f"[red]{e}[/red]")
            raise SystemExit(1) from e
    # ...
    _validate_api_key(output_dir)
    # ...
```
