---
id: ${TIMESTAMP}-refactor-hardcoded-retry-logic
status: todo
title: "Refactor: Make Gemini Client Retry Logic Configurable"
created_at: "${ISO_TIMESTAMP}"
target_module: "src/egregora/orchestration/pipelines/write.py"
assigned_persona: "refactor"
---

## 📋 Refactor: Make Gemini Client Retry Logic Configurable

**Description:**
The retry logic in the `_create_gemini_client` function in `src/egregora/orchestration/pipelines/write.py` is currently hardcoded. This makes it difficult to adjust retry parameters without modifying the source code. The retry settings should be moved into the main Egregora configuration file.

**Context:**
Moving this configuration out of the code will improve flexibility and maintainability. It allows operators to fine-tune performance and error handling for different environments without requiring a new code deployment.

**Code Snippet:**
```python
def _create_gemini_client() -> genai.Client:
    # TODO: [Taskmaster] Refactor hardcoded retry logic to be configurable
    """Create a Gemini client with retry configuration.

    The client reads the API key from GOOGLE_API_KEY environment variable automatically.

    We disable retries for 429 (Resource Exhausted) to allow our application-level
    Model/Key rotator to handle it immediately (Story 8).
    We still retry 503 (Service Unavailable).
    """
    http_options = genai.types.HttpOptions(
        retry_options=genai.types.HttpRetryOptions(
            attempts=3,  # Reduced from 15
            initial_delay=1.0,
            max_delay=10.0,
            exp_base=2.0,
            http_status_codes=[503],
        )
    )
    return genai.Client(http_options=http_options)
```
