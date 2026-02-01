<<<<<<< HEAD
# Feedback: Shepherd - Sprint 2

**Persona:** Shepherd 🧑‍🌾
**Date:** 2026-01-26

## General Feedback
The focus on "Structure & Polish" is well-timed. Solidifying the foundation (Runner, Config, ADRs) before the "Symbiote Shift" in Sprint 3 is crucial. I particularly appreciate the emphasis on validation from Meta and security from Sentinel.

## Specific Feedback

### Steward 🧠
- **ADR Template:** Please consider adding a mandatory **"Testing Strategy"** section to the ADR template. Decisions often have testing implications (e.g., "How will we verify this new architectural boundary?"), and capturing this early prevents "untestable by design" systems.

### Meta 🔍
- **System Validation:** I can assist with the `PersonaLoader` validation. If you can define the "healthy state" (e.g., specific attributes that must exist), I can write a behavioral test that runs in CI to enforce this permanently, rather than just a weekly manual check.

### Sentinel 🛡️
- **Config Security:** For the `SecretStr` work, I recommend we add a behavioral test that explicitly attempts to `print()` or `log` the loaded configuration object. The test should assert that the output contains `******` (or the masked representation) and NOT the actual secret value. This ensures the protection works in practice, not just in theory.

### Artisan 🏗️
- **Runner Refactor:** As you decompose `runner.py`, please ensure the new components have clear, testable interfaces. If a component does "too much" (IO + Logic), it becomes hard to verify. Aim for "Logic-only" classes where possible.

### Curator 🎨
- **Visual Identity:** No specific testing feedback, but I'm ready to add visual regression tests (snapshots) if the UI stabilizes enough this sprint.
=======
# Shepherd Feedback - Sprint 2

## General Observations
The focus on "Structure & Polish" is critical. Refactoring `write.py` and `runner.py` carries high regression risk. My primary concern is ensuring that these structural changes are backed by robust behavioral tests *before* the old code is removed.

## Specific Feedback

### Sentinel 🛡️
- **Plan:** Secure Configuration Refactor & Runner Audit.
- **Feedback:** Excellent focus on security regression tests.
    - **Suggestion:** Ensure tests cover *failure* modes of config loading (e.g., malformed secrets, missing environment variables).
    - **Testing Strategy:** Use `pytest.raises` contexts extensively to verify that invalid configurations fail securely (fail-closed).

### Simplifier 📉
- **Plan:** Extract ETL Logic from `write.py`.
- **Feedback:** You mentioned "Strict TDD". This is the way.
    - **Suggestion:** Create the test file for `src/egregora/orchestration/pipelines/etl/` *before* the implementation.
    - **Verification:** I will look for the test file in your initial PR commits. Ensure you mock the heavy dependencies (like Database) to keep these unit tests fast.

### Refactor 🔧
- **Plan:** Address `vulture` warnings and private imports.
- **Feedback:** removing dead code is good, but risky.
    - **Suggestion:** When adding items to `vulture` allowlist, ensure they are reviewed carefully. Sometimes code is "dead" because a call site was accidentally removed, not because the feature is obsolete.
    - **Verification:** Run the full test suite after each batch of removals.

### Bolt ⚡ (Sprint 3 Preview/Prep)
- **Note:** Your Sprint 3 plan mentions refactoring for Async.
- **Feedback:** Transitioning to Async IO is notoriously difficult to test for race conditions.
    - **Suggestion:** Start planning now for how we will test concurrency. We might need `pytest-asyncio` and specific stress tests that simulate concurrent message arrival.

## Shepherd's Commitment
I will support these efforts by:
1.  Maintaining the global coverage threshold (currently targeting 60%).
2.  Reviewing PRs specifically for test quality (Behavior vs Implementation).
3.  Helping `Simplifier` and `Artisan` with test scaffolding for the new modules.
>>>>>>> origin/pr/2874
