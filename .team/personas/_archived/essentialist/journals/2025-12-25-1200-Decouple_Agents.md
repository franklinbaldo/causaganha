---
title: "💎 Decouple Agents from Data Models"
date: 2025-12-25
author: "Essentialist"
emoji: "💎"
type: journal
---

## 💎 2025-12-25 - Decouple Agents from Data Models

**Observation:** The `EnricherAgent` and `WriterAgent` were both tightly coupled to the `Entry` and `Document` data models, respectively. They were responsible for both generating data via an LLM and then constructing the final data objects. This violated the "Small modules over clever modules" and "Interfaces over implementations" heuristics by mixing concerns and making the agents less reusable.

**Action:** I refactored both agents to focus solely on their core responsibility: interacting with the LLM and returning a simple, data-only Pydantic model (`EnrichmentResult` and `GeneratedPost`). I removed the logic that constructed the final `Entry` and `Document` objects, moving that responsibility to the orchestrator. I also enforced a template-only approach for prompt generation in both agents, adhering to the "Data over logic" principle. The entire process was guided by Test-Driven Development.

**Reflection:** This refactoring simplifies the agents and makes them more modular. By returning simple data objects, they are now easier to test and can be reused in different contexts without modification. The next step should be to review the orchestration layer that calls these agents to ensure it correctly handles the new data-only return values.
