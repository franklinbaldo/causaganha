---
type: "RunCheck"
id: "run-checks/20260914t135010z-do-the-best-useful-work-availab/check-structural-conformance"
run: "runs/20260914T135010Z-do-the-best-useful-work-available-in-this-reposi"
kind: "grounding"
procedure: "uv run wisk check <run> (also runs okf_parser.load_bundle(Path('.wisk/knowledge')).is_conformant under the hood)"
result: "structural.conformant=true, diagnostics=[], concept_count=1145 (up from 1137 before this round's records), markdown_count=1149. The appended wiki bullets and all newly recorded RunReading/RunGoal/RunEvidence/RunCheck files parse as valid OKF instances against the bundle's own schema -- no YAML frontmatter or content-shape regression introduced."
status: "pass"
evidence: "run-evidence/20260914t135010z-do-the-best-useful-work-availab/evidence-wiki-consolidation-diff"
goal: "run-goals/20260914t135010z-do-the-best-useful-work-availab/goal-confirm-pr-1474-and-consolidate"
---

# RunCheck
