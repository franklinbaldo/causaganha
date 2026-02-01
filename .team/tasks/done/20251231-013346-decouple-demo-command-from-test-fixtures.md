---
id: 20251231-013346-decouple-demo-command-from-test-fixtures
status: todo
title: "Decouple the demo command from test fixtures"
created_at: "2025-12-31T01:33:46Z"
target_module: "src/egregora/cli/main.py"
assigned_persona: "refactor"
---

## 📋 Decouple the demo command from test fixtures

**Description:**
The `demo` command in `src/egregora/cli/main.py` currently relies on a hardcoded path to a sample file located in the `tests/fixtures` directory. This creates an undesirable coupling between the application's core logic and its test suite.

**Task:**
Modify the `demo` command to use a more robust method for accessing sample data. This could involve using a tool like `importlib.resources` to package the sample data with the application, making the demo self-contained and independent of the test fixtures.

**Code Snippet:**
```python
# TODO: [Taskmaster] Decouple the demo command from the test fixtures.
@app.command()
def demo(
    # ...
) -> None:
    """Generate a demo site from a sample WhatsApp export."""
    # ...
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        sample_input = project_root / "tests/fixtures/Conversa do WhatsApp com Teste.zip"
        if not sample_input.exists():
            console.print(f"[red]Sample input file not found at {sample_input}[/red]")
            raise typer.Exit(1)
```
