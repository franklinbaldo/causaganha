---
type: AgentReading
id: "2026-09-26-exciting-mccarthy-bomtmk-reading-issues"
run_id: "2026-09-26-exciting-mccarthy-bomtmk"
subject: "open_issues"
reference: "GitHub issues, franklinbaldo/causaganha (list_issues, state=OPEN, 21 total) + knowledge/backlog/issue-1050.md + knowledge/backlog/issue-1051.md"
finding: "21 open issues, unchanged in count since round kgxf50 earlier today. #1050/#1051 (segmenter corpus + independent adjudication) remain the only unblocked, actively-progressing track with a concrete, mechanically-checkable next step and no external-credential dependency. Live scripts/segmenter_governance_status.py at session start: document_count=197, review_count=37, val_count=30 (at RFC 0012 ceiling), test_count=7 (of a 30 floor) -- exactly matching round kgxf50's final result_summary, confirming no other round has touched the segmenter store since. #950/#951/#1093 and the Parquet/CNJ/TCU/TSE cluster (#1470/#1469/#1471/#1472/#1468/#1022/#985) remain blocked on GCP/IA credentials this session lacks, per 16+ prior rounds -- reconfirmed by their updated_at timestamps showing no new activity since the last check, not re-investigated in depth."
---

# Reading: open issues + segmenter backlog state

`mcp__github__list_issues` (state=OPEN, 21 total) plus a full read of
`knowledge/backlog/issue-1050.md` and `knowledge/backlog/issue-1051.md`.

**#1051** (`segmenter: build an independently annotated validation set
for model selection`) — status `unblocked`. As of round `kgxf50`
(2026-09-26, merged as PR #1670/#1671-superseded-by-#1672):
`document_count=197`, `review_count=37`, `val_count=30` (already at its
RFC 0012 ceiling), `test_count=7` (of a 30 floor). Verified live at this
round's start via `scripts/segmenter_governance_status.py` — identical
numbers, confirming the store is exactly where `kgxf50` left it. The
backlog's own `next_move` is explicit: keep adjudicating single-
annotated, `seeded_with=='none'`, unreviewed candidates, always
simulating `assign_splits` (isolated, then jointly) before spending
annotation effort, and re-run the **full** test suite (not just
`tests/segmenter_dataset`) before finalizing any adjudication — a
process lesson `kgxf50` learned the hard way (see its
`decision-preserve-audit-allowlist-precedent`).

**#1050** (`segmenter: repair and scale the real training corpus with
agent annotation`) — status `unblocked`. Corpus-scale ceiling already
reached 30/30 since round `ku8qje`; no further corpus growth is
strictly required to keep advancing #1051's floor.

**Re-confirmed blocked, not re-investigated (established by 16+ prior
rounds, most recently `uz8msx`/`kgxf50` today):** #950
(`product(mcp): disponibilizar endpoint remoto`) and downstream
#951/#1093 — needs GCP Cloud Run deploy credentials this session lacks.
#1470/#1471/#1472/#1468/#1469/#1022/#985 (Parquet/CNJ regeneration,
TCU/TSE Internet Archive publication) — need live IA/GCP write access
this session does not have.

**#1053-1057/#884/#886/#887** — longer-horizon segmenter experiment
issues gated on the #1051 val/test floor being met first. Not
selectable yet.

**Decision driver:** #1051's adjudication track remains the only open
issue that is unblocked, has a proven TDD-shaped mechanism exercised by
4 prior rounds this same day, and has a crisp, live-checkable
`success_signal` (`test_count` strictly increasing, verified via
`scripts/segmenter_governance_status.py`). Selected as this round's
primary goal, continuing the same-day track rather than starting a new
one.
