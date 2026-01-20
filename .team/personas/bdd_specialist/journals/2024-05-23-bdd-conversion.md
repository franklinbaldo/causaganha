---
title: "🥒 BDD Conversion: Model Key Rotation"
date: 2024-05-23
author: "Specifier"
emoji: "🥒"
type: journal
focus: "BDD Conversion"
---

# Feature: Model Key Rotation

## Original Tests
- `tests/test_model_key_rotator.py`

## New Scenarios
- [x] Scenario 1: Exhaust keys per model before switching models (Happy Path with retries)
- [x] Scenario 2: Fail when all models and keys are exhausted (Error Path)
- [x] Scenario 3: Succeed on first try (Happy Path)

## Challenges
- The original tests used a `nonlocal` variable for `call_count` inside the mock. In the BDD step, I used a dictionary `context` to share state between steps and the mock function. This is a common pattern in BDD to maintain state across the scenario.

## Next Steps
- Convert `tests/test_command_processing.py` to BDD.
