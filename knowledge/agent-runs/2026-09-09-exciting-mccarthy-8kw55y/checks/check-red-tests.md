---
type: AgentCheck
id: "2026-09-09-exciting-mccarthy-8kw55y-check-red-tests"
run_id: "2026-09-09-exciting-mccarthy-8kw55y"
command: "uv run pytest tests/test_render_queries.py -k \"lawyer_ratings or ratings_history\" -v (run before implementing the fix)"
result: "failed"
evidence_id: "2026-09-09-exciting-mccarthy-8kw55y-evidence-red-tests"
summary: "2 failed (test_register_lawyer_ratings_falls_back_to_ia_when_local_absent, test_register_ratings_history_falls_back_to_ia_when_local_absent), 1 passed, 44 deselected -- confirms the bug is live."
---

# Check: RED antes da correção
