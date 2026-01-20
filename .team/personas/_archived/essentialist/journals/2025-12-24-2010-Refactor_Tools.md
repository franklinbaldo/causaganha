---
title: "💎 Refactoring Tools for Data-Driven Simplicity"
date: 2025-12-24
author: "Essentialist"
emoji: "💎"
type: journal
---

## 💎 2025-12-24 - Refactoring Tools for Data-Driven Simplicity
**Observation:** The 'tools.py' module contained imperative, hardcoded logic for repository lookups, violating the 'Data over logic' heuristic. Specifically, the 'count_documents_by_type' function had its own implementation for routing to the correct repository.
**Action:** I refactored the 'ContentLibrary' to centralize this logic. I added a 'count' method to provide a single point of access for all repositories. I then simplified the tool functions in 'tools.py' to use these new, centralized methods. This change removed the redundant logic and aligned the code with the 'Data over logic' principle. The entire process was guided by Test-Driven Development.
