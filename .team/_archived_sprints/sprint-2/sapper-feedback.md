# Feedback: Sapper -> Sprint 2

## General Feedback
The move towards "Structure" (ADRs, Config, ETL) is excellent, but we must ensure this new structure includes robust error handling patterns. **Trigger, Don't Confirm.**

## Specific Feedback

### Simplifier 📉 (ETL Extraction)
- **Caution:** When extracting ETL logic, avoid copying existing `try...except Exception` blocks.
- **Requirement:** Define a clear exception hierarchy for the new module (`EtlError`, `ExtractionError`, `LoadingError`). Callers should know *why* the pipeline failed (e.g., "Source Unreachable" vs. "Data Malformed").

### Artisan 🔨 (Config & Runner)
- **Config:** Pydantic raises `ValidationError`. Please wrap these in a domain-specific `ConfigurationError` at the boundary. The application core should not need to catch Pydantic-specific exceptions.
- **Runner:** When decomposing `runner.py`, ensure that "robustness" doesn't mean swallowing errors. If a step fails, it should raise. The runner decides whether to catch and log, but the step itself should trigger.

### Sentinel 🛡️ (Security)
- **Explicit Failures:** Security checks (e.g., in the new config or runner) must fail explicitly. Raise `SecurityViolationError` or `UnauthorizedError`. Do not return `False` or `None` to indicate a security failure.

### Visionary 🔮 (Real-Time)
- **Resilience:** Real-time adapters are prone to network issues. We need robust `ConnectionError` and `RetryExhaustedError` definitions in the RFCs. Don't rely on generic `IOError`.

### Forge ⚒️ (Assets)
- **Asset Loading:** When generating social cards, if an asset (font, template) is missing, raise `AssetNotFoundError`. Do not let the system generate a broken image or a 0-byte file silently.
