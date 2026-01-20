---
title: "🤠 Site Scaffolding Fixes"
date: 2025-12-24
author: "Sheriff"
emoji: "🤠"
type: journal
---

## 🤠 2025-12-24 - Site Scaffolding Failures
**Observation:** Two tests were failing in the test suite: `test_main_py_and_overrides_in_egregora_dir` and `test_mkdocs_build_with_material`. The first was due to the `overrides` directory being created in the wrong location, and the second was caused by an incorrect `docs_dir` path in the generated `mkdocs.yml`.
**Action:** I corrected the path for the `overrides` directory in `src/egregora/output_adapters/mkdocs/scaffolding.py` and updated the `mkdocs.yml.jinja` template to use the correct `docs_dir` variable. I then verified that both tests passed and that the entire test suite is stable.
