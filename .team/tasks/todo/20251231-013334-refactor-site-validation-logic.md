---
id: 20251231-013334-refactor-site-validation-logic
status: todo
title: "Refactor site validation logic into a reusable utility"
created_at: "2025-12-31T01:33:34Z"
target_module: "src/egregora/cli/main.py"
assigned_persona: "artisan"
---

## 📋 Refactor site validation logic into a reusable utility

**Description:**
The `top` and `show_reader_history` functions in `src/egregora/cli/main.py` both contain duplicated code for validating the existence of a site's `.egregora` directory and database file. This duplicated logic makes the code harder to maintain.

**Task:**
Create a reusable utility function that takes a `site_root` path and performs all necessary validations. Replace the duplicated code in both functions with a call to this new utility.

**Code Snippet:**
```python
# TODO: [Taskmaster] Refactor site validation logic into a reusable utility function.
@app.command()
def top(
    site_root: Annotated[
        Path,
        typer.Argument(help="Site root directory containing .egregora/config.yml"),
    ],
    # ...
) -> None:
    """Show top-ranked posts without running evaluation."""
    site_root = site_root.expanduser().resolve()

    # Verify .egregora directory exists
    egregora_dir = site_root / ".egregora"
    if not egregora_dir.exists():
        console.print(f"[red]No .egregora directory found in {site_root}[/red]")
        console.print("Run 'egregora init' or 'egregora write' first to create a site")
        raise typer.Exit(1)
```
