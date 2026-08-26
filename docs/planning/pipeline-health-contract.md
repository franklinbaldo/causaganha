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

## Publication-clock evidence

The third clock must be read from evidence that proves the **authoritative public
state was incorporated**, not from cron, GitHub workflow timestamps, or the newest
content row.

| Pipeline | Evidence accepted for `last publication` | Current boundary |
| --- | --- | --- |
| DataJud | `published_at` inside the verified coherent state bundle | Direct and authoritative. Older bundles without the field are `unknown`, not inferred from content timestamps. |
| TJRO JURIS | Modification timestamp of the published `tjro-juris-manifest.csv` object, provided by the same Internet Archive authority from which continuity restores | Valid only when the manifest object itself is readable and its object timestamp is exposed. Missing timestamp is `unknown`. |
| STJ Acórdãos | Modification timestamp of the published `stj-manifest.csv` object, provided by the same Internet Archive authority from which continuity restores | Same rule as TJRO: object timestamp, never newest row `updated_at`. |
| DJEN | Timestamp of the **latest component that participates in the coherent published materialization** (`sync-manifest.parquet` plus any still-pending `manifest-log/` segment) | Composite authority: a timestamp for the parquet alone is insufficient when newer segments exist. Until the strict published reader can expose component-level publication metadata coherently, the publication clock is `unknown`. |

The distinction above is intentional. An `updated_at`/`consultado_em` stored in a
manifest row is a **content-state clock**. It may be useful operationally but it
does not prove when that state became public. Likewise, an HTTP transport failure
while probing publication metadata must not turn a successfully-read dataset into
an empty dataset; it affects only the publication-clock observation.

Publication-clock states should therefore be explicit when implemented:

- `present`: the authoritative object/generation proves a publication timestamp;
- `absent`: the authoritative published state itself is proven absent;
- `unknown`: the state is present but its publication timestamp cannot be proven;
- `unavailable`: the authority needed to establish the clock could not be verified.

No fallback from `unknown`/`unavailable` to `ultima_atualizacao`, workflow success,
cron time, Git commit time, or wall-clock age is permitted.

## Canary boundary

- DJEN keeps the existing end-to-end published canary.
- DataJud should prove published state plus one cheap public query.
- STJ should prove reachability/structure of the published artifact; source WAF
  reachability is not a required live-health property.
- TJRO JURIS should prove the published artifact and represent known source-network
  limitations explicitly rather than turning them into false red/green claims.

## Next gate

`ultima_tentativa` and `ultimo_sucesso` already have a bounded factual observer in
`causaganha_mcp.workflow_runs`. The next implementation slice should add the
publication-clock observation above and compose all three clocks into
`causaganha_status` without collapsing their states.

For DJEN, that slice must first make the strict published reader expose coherent
component publication metadata; a parquet-only timestamp is explicitly rejected.
For TJRO/STJ, reuse the same manifest object already read for status rather than
inventing a second store. DataJud should continue to use the bundle's own
`published_at`.

Only after the three series exist should #892 freeze threshold policy. Any future
`healthy/stale` rule must state which clock it uses and why; it must not infer
publication from workflow success or freshness from the newest content row.
