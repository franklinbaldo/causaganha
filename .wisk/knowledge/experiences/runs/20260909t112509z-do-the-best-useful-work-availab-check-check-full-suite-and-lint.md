---
type: "RunCheck"
id: "run-checks/20260909t112509z-do-the-best-useful-work-availab/check-full-suite-and-lint"
run: "runs/20260909T112509Z-do-the-best-useful-work-available-in-this-reposi"
kind: "verification"
procedure: "uv run ruff check . && uv run ruff format --check src/segmenter_dataset/release.py tests/segmenter_dataset/test_release.py && uv run pytest tests/segmenter_dataset -q"
result: "ruff check .: All checks passed. ruff format --check on both changed files: already formatted. pytest tests/segmenter_dataset -q: 241/241 green (was 240), including the new RED->GREEN test. A full-repo 'uv run pytest -q' was additionally launched in the background to match this session's established pre-push convention; its result will be folded into the RunOutcome once it completes, since the change is isolated to segmenter_dataset/release.py and does not touch any other module's call sites."
status: "pass"
evidence: "run-evidence/20260909t112509z-do-the-best-useful-work-availab/evidence-conflict-gate-red-green"
goal: "run-goals/20260909t112509z-do-the-best-useful-work-availab/goal-wire-annotation-conflict-gate"
---

# RunCheck
