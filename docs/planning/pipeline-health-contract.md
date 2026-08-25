# Pipeline health contract — temporal semantics

Issue: #892.

This document freezes the vocabulary used before any `healthy` / `stale` /
`degraded` threshold is introduced. It deliberately does **not** classify any
pipeline as healthy.

## Common clocks

The four pipelines expose three different events and they must not be collapsed:

1. **attempt** — a scheduled or manually dispatched workflow run starts;
2. **success** — that workflow run completes with `conclusion=success`;
3. **publication** — the pipeline's authoritative public artifact incorporates a
   coherent generation/state.

A successful run may legitimately publish nothing new. Conversely, the age of a
content entry is not the time of the most recent workflow attempt. Future health
logic must therefore retain these clocks independently.

Current timestamps/counts/errors are operational state and must not be authored
in OKF Markdown. The `Pipeline` relation stores only stable identity, workflow,
cron cadence, clock definitions and canary capability.

## Frozen cadence

| Pipeline | Workflow | Scheduled opportunity |
| --- | --- | --- |
| DJEN | `.github/workflows/collect-zips.yml` | `*/20 * * * *` |
| STJ Acórdãos | `.github/workflows/stj-sync.yml` | `0 7 * * *` |
| TJRO JURIS | `.github/workflows/tjro-sync.yml` | `0 9 * * *` |
| DataJud | `.github/workflows/datajud-enrich.yml` | `13 5 * * *` |

Cron is an **opportunity cadence**, not a freshness guarantee. GitHub scheduling,
source availability, resumable backfill, rate limits and “nothing new” outcomes
all make `now - cron_tick` an invalid health metric by itself.

## Publication authority

Publication remains pipeline-specific and published-first:

- DJEN: coherent `sync-manifest.parquet` plus `manifest-log/` state on Internet Archive;
- TJRO JURIS: the public manifest/parquets used for restore/continuity;
- STJ: the public manifest/resources used for restore/continuity;
- DataJud: coherent `datajud-state-{tribunal}.zip` bundle.

`present` / `absent` / `unavailable` continue to describe whether that authority
could be observed. They are not health verdicts.

## Canary boundary

- DJEN keeps the existing end-to-end published canary.
- DataJud should prove published state plus one cheap public query.
- STJ should prove reachability/structure of the published artifact; source WAF
  reachability is not a required live-health property.
- TJRO JURIS should prove the published artifact and represent known source-network
  limitations explicitly rather than turning them into false red/green claims.

## Next gate

The next implementation slice may collect **last attempt**, **last successful
run**, and **last publication** as dynamic observations. Only after those three
series exist should #892 freeze threshold policy. Any future `healthy/stale`
rule must state which clock it uses and why; it must not infer publication from
workflow success or freshness from the newest content row.
