# Plan: Sapper - Sprint 3

**Persona:** Sapper 💣
**Sprint:** 3
**Created:** 2026-01-26
**Priority:** Medium

## Objectives
My mission is to prepare the system for the unpredictability of "Real-Time" and "LLM-driven" inputs (The Symbiote).

- [ ] **Define Real-Time Exceptions:** Create a robust exception hierarchy for real-time streams (`ConnectionError`, `StreamInterrupted`, `MessageMalformed`) to support Visionary's RFC.
- [ ] **Harden LLM Parsing:** Ensure the "Structured Data Sidecar" parses LLM outputs robustly. If parsing fails, raise `LlmParsingError` with the raw response attached, rather than returning `None`.
- [ ] **Refactor Input Adapter Base:** Collaborate with Artisan to refactor the `InputAdapter` protocol to enforce standard exception handling across all adapters.

## Dependencies
- **Visionary:** I need the RFCs for the real-time adapter to understand the failure modes.
- **Builder/Visionary:** I need access to the "Structured Data Sidecar" code.

## Context
In Sprint 3, we introduce external chaos (Real-time streams, LLM outputs). The system must be able to "Trigger" on specific failures (e.g., "RateLimitExceeded" vs "ContextWindowExceeded") to allow for intelligent recovery strategies.

## Expected Deliverables
1.  **New Module:** `src/egregora/realtime/exceptions.py`.
2.  **Refactored Sidecar:** Parsing logic in the Sidecar uses explicit exceptions.
3.  **Updated Protocol:** `InputAdapter` defines required exceptions.

## Risks and Mitigations
| Risk | Probability | Impact | Mitigation |
|-------|---------------|---------|-----------|
| LLM Errors are swallowed | High | High | I will create specific tests that inject malformed LLM responses. |
