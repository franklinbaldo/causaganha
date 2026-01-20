---
id: 20251231-033255-refactor-api-key-validation
status: todo
title: "Refactor API key validation for clarity and separation of concerns"
created_at: "2025-12-31T03:32:55Z"
target_module: "src/egregora/orchestration/pipelines/write.py"
assigned_persona: "refactor"
---

## Description

The `_validate_api_key` function in `src/egregora/orchestration/pipelines/write.py` is overly complex and mixes responsibilities. It handles environment variable loading, key validation, and user-facing error reporting, making it difficult to test and maintain.

## Task

Refactor the function to:
1.  **Separate Concerns:** Create distinct functions for loading keys, validating them, and formatting error messages.
2.  **Improve Clarity:** Simplify the nested conditional logic to make the validation flow easier to follow.
3.  **Enhance Testability:** The refactored functions should be pure and easier to unit test without relying on environment variables or console output.

## Code Snippet

```python
# TODO: [Taskmaster] Refactor API key validation for clarity and separation of concerns
def _validate_api_key(output_dir: Path) -> None:
    """Validate that API key is set and valid."""
    skip_validation = os.getenv("EGREGORA_SKIP_API_KEY_VALIDATION", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }

    api_keys = get_google_api_keys()
    if not api_keys:
        _load_dotenv_if_available(output_dir)
        api_keys = get_google_api_keys()

    if not api_keys:
        console.print("[red]Error: GOOGLE_API_KEY (or GEMINI_API_KEY) environment variable not set[/red]")
        console.print(
            "Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable with your Google Gemini API key"
        )
        console.print("You can also create a .env file in the output directory or current directory.")
        raise SystemExit(1)

    if skip_validation:
        os.environ["GOOGLE_API_KEY"] = api_keys[0]
        return

    console.print("[cyan]Validating Gemini API key...[/cyan]")
    validation_errors: list[str] = []
    for key in api_keys:
        try:
            validate_gemini_api_key(key)
            os.environ["GOOGLE_API_KEY"] = key
            console.print("[green]✓ API key validated successfully[/green]")
            return
        except ValueError as e:
            validation_errors.append(str(e))
        except ImportError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise SystemExit(1) from e

    joined = "\n\n".join(validation_errors)
    console.print(f"[red]Error: {joined}[/red]")
    raise SystemExit(1)
```
