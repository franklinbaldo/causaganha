---
type: AgentReading
id: "2026-09-26-exciting-mccarthy-kgxf50-reading-issues"
run_id: "2026-09-26-exciting-mccarthy-kgxf50"
subject: "open_issues"
reference: "GitHub issues, franklinbaldo/causaganha (list_issues, state=OPEN, 21 total) + knowledge/backlog/issue-1050.md + knowledge/backlog/issue-1051.md"
finding: "21 open issues. #1050/#1051 (segmenter corpus + independent adjudication) are the only unblocked, actively-progressing track with a concrete next step and no external-credential dependency. #950/#951/#1093 blocked on GCP Cloud Run deploy credentials unavailable to this session (re-confirmed, not re-investigated). #1470-1472/#1468-1469/#1022/#985 (Parquet/CNJ, TCU, TSE) are data-pipeline work also gated on IA/GCP credentials per 15+ prior rounds' backlog notes."
---

# Reading: open issues + segmenter backlog state

`mcp__github__list_issues` (state=OPEN, 21 total) plus a full read of
`knowledge/backlog/issue-1050.md` and `knowledge/backlog/issue-1051.md`
(the two files this round's work depends on).

**#1051 (`segmenter: build an independently annotated validation set for
model selection`)** — status `unblocked`. As of round `p08457`
(2026-09-26, merged as PR #1668/#1669): `document_count=197`,
`review_count=34`, `val_count=30` (at its RFC 0012 ceiling already),
`test_count=4` (of a 30 floor). `meets_rfc_0012_split_floor` is `False`.
The backlog file's own `next_move` is explicit and mechanically
checkable: keep adjudicating single-annotated, `seeded_with=='none'`,
unreviewed candidates, always **simulating** `assign_splits` first
(isolated, then jointly with the round's batch) before spending
annotation effort, because only the aggregate test_count/val_count is a
controllable, checkable contract (which specific document lands in
val vs. test is not). At the start of round `p08457`, 141 such
candidates existed, 134 of which individually moved `test_count` in
isolation.

**#1050 (`segmenter: repair and scale the real training corpus with
agent annotation`)** — status `unblocked`, `category: ml_data_work`.
27+ real batches already ingested via
`scripts/ingest_djen_sample_technique1_batch.py` across ~25 tribunals;
Lote 28 (round `ku8qje`) crossed the RFC 0012 §5 item 4 corpus-scale
ceiling (document_count 195->197), which is what unblocked #1051's
remaining gap to be pure adjudication coverage rather than corpus size.
No new corpus growth is strictly required this round unless a batch of
`#1051` candidates runs out (unlikely at 141 eligible candidates).

**Re-confirmed blocked, not re-investigated in depth (established by
15+ prior rounds, most recently round `uz8msx` this same day):**
#950 (`product(mcp): disponibilizar endpoint remoto`) and its two
downstream issues #951/#1093 — needs an authenticated
`deploy-mcp.yml` Cloud Run deploy this session has no GCP credentials
for. #1470/#1471/#1472/#1468/#1469/#1022/#985 (Parquet/CNJ regeneration,
TCU/TSE Internet Archive publication) — need live IA/GCP write access
this session does not have. These are read as still-blocked, not
selected for work.

**#1053-1057/#884/#886/#887** — longer-horizon segmenter experiment
issues (active-learning rounds, encoder benchmarks, holdout
qualification) that depend on the #1051 val/test floor being met
first (RFC 0012's own dependency chain: model-selection experiments
need the split floor before their results are trustworthy). Not
selected this round — #1051 is the direct prerequisite and the
better-scoped unit of work.

**Decision driver:** #1051's adjudication track is the only open issue
that is (a) unblocked, (b) has a proven, TDD-shaped mechanism already
exercised by 3+ prior rounds this week, and (c) has a crisp, live-checkable
`success_signal` (`test_count` strictly increasing, verified via
`scripts/segmenter_governance_status.py`). Selected as this round's
primary goal.
