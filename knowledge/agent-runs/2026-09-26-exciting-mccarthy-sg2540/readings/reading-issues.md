---
type: AgentReading
id: "2026-09-26-exciting-mccarthy-sg2540-reading-issues"
run_id: "2026-09-26-exciting-mccarthy-sg2540"
subject: "open_issues"
reference: "GitHub issues, franklinbaldo/causaganha (list_issues, state=OPEN, 21 total) + knowledge/backlog/issue-1050.md + knowledge/backlog/issue-1051.md"
finding: "21 open issues. #1051 (segmenter independent-annotation val/test floor, RFC 0012 Sec 5 item 4) remains the only unblocked, actively-progressing track: live scripts/segmenter_governance_status.py at session start showed document_count=197, review_count=48, val_count=30 (at its corpus-scale ceiling), test_count=18 (still behind the 30 floor). All credential-blocked issues (#950/#951/#1093 GCP Cloud Run; #1470/#1469/#1471/#1472/#1468/#1022/#985 Internet Archive/Parquet) remain blocked with no new signal since round bomtmk earlier today; the segmenter experiment backlog (#1053-1057/#884/#886/#887) still gates on #1051's floor. No open PRs exist against the repo at session start."
---

# Reading: open issues + segmenter backlog state

`mcp__github__list_issues` (state=OPEN, 21 total) plus a full read of
`knowledge/backlog/issue-1050.md` and `knowledge/backlog/issue-1051.md`,
plus `mcp__github__list_pull_requests` (state=open, 0 results).

**#1051** (`segmenter: build an independently annotated validation set
for model selection`) -- status `unblocked`. Live
`scripts/segmenter_governance_status.py` at this round's start:
`document_count=197`, `annotation_count=271`, `review_count=48`,
`val_count=30` (at its RFC 0012 corpus-scale ceiling),
`test_count=18` (of the 30 floor) -- exactly matching the merge note at
the end of `knowledge/backlog/issue-1051.md` (rounds pg2bcv/uq3be8's
combined PR #1677+#1678 merge), confirming no other round touched the
store since. The backlog's own next step is explicit: keep
adjudicating single-annotated, `seeded_with=='none'`, unreviewed
candidates, always simulating `assign_splits` (isolated, then jointly)
before spending annotation effort, verify every subagent's tagged
reproduction for silently-dropped NBSP/whitespace before trusting a
"verbatim" self-check, and re-run the full test suite plus
`scripts/segmenter_semantic_audit.py` *during* adjudication, not only
at the end, since an adjudicated review's own span choice or an
ingested annotation's own span choice can introduce a fresh
zero-tolerance anti-pattern finding.

**#1050** (`segmenter: repair and scale the real training corpus`) --
corpus-scale ceiling already at 30/30 since round `ku8qje`; no further
growth strictly required for #1051's floor.

**Reconfirmed blocked, not re-investigated (established by 16+ prior
rounds today and earlier):** #950/#951/#1093 (GCP Cloud Run deploy
credentials absent this session); #1470/#1471/#1472/#1468/#1469/#1022/#985
(Internet Archive/GCP write credentials absent this session).

**#1053-1057/#884/#886/#887** -- gated on #1051's val/test floor,
not yet selectable.

**No open PRs** exist at session start (`list_pull_requests` returned
an empty array) -- the repo's default branch (`origin/main`, commit
`36013b4`) is the base for this round's work; a stale local branch
head was reset to it before starting (see `check-branch-state`).

**Decision driver:** #1051 remains the only open issue that is
unblocked, has a proven TDD-shaped mechanism exercised by 8+ prior
rounds, and has a crisp, live-checkable `success_signal`. Selected as
this round's primary goal.
