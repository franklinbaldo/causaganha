---
type: "RunCheck"
id: "run-checks/20260910t035023z-do-the-best-useful-work-availab/check-grounding"
run: "runs/20260910T035023Z-do-the-best-useful-work-available-in-this-reposi"
kind: "grounding"
procedure: "okf-parser check .wisk/knowledge (no separate relational schema for this bundle -- per-type .schema.sql specs live under .wisk/specs/ and are applied by wisk's own runtime, not okf-parser check's --relational-schema flag)"
result: "conformant:true, concept_count 776 (up from 774 pre-edit: two new lineage bullets did not create new concepts, but the goal/evidence/reading files recorded this round did), 0 diagnostics, markdown_count 780, reserved_count 4. The wiki edit (nineteenth pattern paragraph + two lineage bullets) parses as valid Markdown/OKF and did not break the WikiEntry's frontmatter or structure."
status: "pass"
---

# RunCheck
