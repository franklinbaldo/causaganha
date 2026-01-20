---
title: "💎 Refactor Agents for Declarative Purity"
date: "2025-12-25"
author: "Essentialist"
emoji: "💎"
type: journal
---

## 💎 2025-12-25 - Refactor Agents for Declarative Purity
**Observation:** The `WriterAgent` and `EnricherAgent` classes contained several violations of the Essentialist Heuristics. They used imperative logic (hardcoded Python strings) to build prompts, had complex conditional paths for configuration (`use_templates`), and relied on implicit "magic strings" (`model="test"`) for test setup. This made them difficult to maintain and less declarative.

**Action:** I refactored both agents to be purely declarative by moving all prompt logic into external Jinja2 templates. I removed the conditional `use_templates` flag from `WriterAgent`, enforcing a single, declarative path. I also decoupled test configuration by introducing an explicit `.for_test()` factory method on both agents, eliminating the "magic string" dependency. The entire process was guided by strict Test-Driven Development (TDD) to ensure safety and correctness.

**Reflection:** The pattern of using a `.for_test()` class method is a highly effective way to enforce the "Explicit over implicit" heuristic at the boundary between application code and test code. It cleanly separates concerns and avoids polluting the production `__init__` with test-specific logic. This pattern should be considered a convention for future agent development. The next iteration could focus on applying the "Data over logic" principle to the agent's internal decision-making, such as routing between different prompt strategies based on entry metadata rather than conditional code.
