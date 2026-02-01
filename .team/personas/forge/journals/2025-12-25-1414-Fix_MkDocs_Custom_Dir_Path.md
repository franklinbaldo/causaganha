---
title: "⚒️ Fix MkDocs Custom Directory Path"
date: 2025-12-25
author: "Forge"
emoji: "⚒️"
type: journal
---

## ⚒️ 2025-12-25 - Correct MkDocs `custom_dir` Path

**Observation:** The `custom_dir` path in `mkdocs.yml` was configured to `overrides` at the site root, which was a temporary workaround. The intended architecture was to have the `overrides` directory located within the `.egregora` directory for better project organization.

**Action:** I implemented the required changes to revert the workaround.
1.  Modified `src/egregora/rendering/templates/site/mkdocs.yml.jinja` to set `custom_dir: overrides`. Since `mkdocs.yml` is generated inside `.egregora`, this relative path correctly points to a sibling `overrides` directory.
2.  Updated `src/egregora/output_sinks/mkdocs/scaffolding.py` to ensure the `overrides` directory is created at `.egregora/overrides` during site scaffolding.
3.  Adjusted the test `tests/unit/output_sinks/mkdocs/test_scaffolding.py` to assert that the `overrides` directory is in the correct new location, ensuring the fix is verified by the test suite.

**Reflection:** This task highlighted the importance of understanding file-relative configurations. The automated code review was incorrect because it missed that the `custom_dir` path is relative to the `mkdocs.yml` file's own location. Trusting the Test-Driven Development (TDD) cycle, where the tests passed after the correction, was essential to delivering a working solution despite the faulty review. For future tasks involving path configurations, I will double-check the base location from which paths are resolved.
