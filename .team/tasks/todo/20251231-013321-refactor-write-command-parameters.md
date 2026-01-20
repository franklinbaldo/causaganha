---
id: 20251231-013321-refactor-write-command-parameters
status: todo
title: "Refactor write command to use a Pydantic model"
created_at: "2025-12-31T01:33:21Z"
target_module: "src/egregora/cli/main.py"
assigned_persona: "refactor"
---

## 📋 Refactor write command to use a Pydantic model for its parameters

**Description:**
The `write` function in `src/egregora/cli/main.py` has an excessive number of parameters. This makes the function signature long and difficult to manage.

**Task:**
Refactor the `write` function to accept a single Pydantic model that encapsulates its configuration options. This will improve readability, maintainability, and allow for easier validation.

**Code Snippet:**
```python
# TODO: [Taskmaster] Refactor the write command to use a Pydantic model for its parameters.
@app.command()
def write(
    input_file: Annotated[Path, typer.Argument(help="Path to chat export file (ZIP, JSON, etc.)")],
    *,
    output: Annotated[
        Path, typer.Option("--output-dir", "-o", help="Directory for the generated site")
    ] = Path("site"),
    source: Annotated[
        SourceType, typer.Option("--source-type", "-s", help="Source format of the input")
    ] = SourceType.WHATSAPP,
    # ... and many more parameters
) -> None:
```
