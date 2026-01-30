# CausaGanha Data Pipeline Architecture

## Mission: Backfill Campaign (24/7 Data Collection)

```
GOAL: Collect years of historical DJEN data continuously
APPROACH: Self-aware, rate-limited jobs that work in parallel
CONSTRAINT: Each job finishes in <10 min to allow others to run next cycle

Timeline:
- Cycle every 5 minutes
- Each job works for up to 10 minutes
- Then exits to let other jobs run
- Gradually fills entire backlog
```

---

## Current (Broken) Architecture

```mermaid
graph TD
    subgraph "Current State - PROBLEMATIC"
        Schedule["Cron Schedules<br/>(Different for each job)"]

        subgraph "Every 5 min"
            Collect["COLLECT<br/>lock: pipeline-collect"]
        end

        subgraph "Every 10 min"
            Consolidate["CONSOLIDATE<br/>lock: pipeline-consolidate"]
        end

        subgraph "Every hour at :05"
            Embed["EMBED<br/>lock: pipeline-embed"]
        end

        subgraph "Daily at 6 AM"
            Catalog["CATALOG<br/>always runs"]
        end

        Schedule --> Collect
        Schedule --> Consolidate
        Schedule --> Embed
        Schedule --> Catalog

        style Collect fill:#ff6b6b
        style Consolidate fill:#ff6b6b
        style Embed fill:#ff6b6b
        style Catalog fill:#ffa94d
    end

    Problems["❌ PROBLEMS:<br/>- Per-job locks prevent parallelization<br/>- Different cron schedules<br/>- Jobs don't know what work to do<br/>- Consolidate takes 19-20 min<br/>- Multiple workflows can run simultaneously<br/>- No conditional triggers"]

    style Problems fill:#ffe0e0
```

## Desired (Fixed) Architecture - Time-Sliced Backfill

```mermaid
graph TD
    subgraph "BACKFILL PHASE (Now - 24/7)"
        Schedule["Every 5 minutes<br/>(continuous harvest)"]

        Lock["🔒 GLOBAL LOCK<br/>Only 1 workflow at a time<br/>group: pipeline-global"]

        Schedule --> Lock

        subgraph "ALL IN PARALLEL (Timeout: 10 minutes)"
            Collect["COLLECT<br/>- Work for UP TO 10 min<br/>- Download from DJEN<br/>- Upload to IA<br/>- Exit when done or time runs out<br/>- Output: files_added=true/false"]

            Consolidate["CONSOLIDATE<br/>- Work for UP TO 10 min<br/>- Convert complete days<br/>- Exit when done or time runs out<br/>- Output: files_added=true/false"]

            Embed["EMBED<br/>- Work for UP TO 10 min<br/>- Generate embeddings<br/>- Exit when done or time runs out<br/>- Output: files_added=true/false"]
        end

        Lock --> Collect
        Lock --> Consolidate
        Lock --> Embed

        Collect -.->|parallel| Consolidate
        Consolidate -.->|parallel| Embed
        Embed -.->|outputs| DependCheck{Any files added?}

        DependCheck -->|YES| Catalog["CATALOG<br/>- Rebuild manifest<br/>- Takes ~5-15 min<br/>- Output: catalog_updated=true/false"]
        DependCheck -->|NO| SkipCatalog["SKIP CATALOG"]

        Catalog --> DashCheck{Catalog updated?}
        DashCheck -->|YES| Dashboard["DASHBOARD-CACHE<br/>- Regenerate"]
        DashCheck -->|NO| SkipDash["SKIP DASHBOARD"]

        style Collect fill:#51cf66
        style Consolidate fill:#51cf66
        style Embed fill:#51cf66
        style Catalog fill:#4dabf7
        style Dashboard fill:#b197fc
        style SkipCatalog fill:#868e96
        style SkipDash fill:#868e96
    end

    Benefits["✅ BENEFITS FOR BACKFILL:<br/>- Continuous 24/7 harvesting<br/>- Each job gets turn every 5 min<br/>- No starvation (alternating priority)<br/>- Gradual coverage of years of data<br/>- Self-healing (incomplete days caught later)<br/>- Observable progress"]

    style Benefits fill:#e0f2e0
```

---

## Current (Broken) Architecture

```mermaid
graph TD
    subgraph "Fixed State - CORRECT"
        Schedule["Single Global Schedule<br/>Every 5 minutes"]

        Lock["🔒 GLOBAL CONCURRENCY LOCK<br/>Only 1 workflow runs at a time<br/>group: pipeline-global<br/>cancel-in-progress: false"]

        Schedule --> Lock

        subgraph "Within Same Workflow - ALL IN PARALLEL"
            Collect["COLLECT<br/>- Check: New DJEN data?<br/>- If YES → Download & Upload<br/>- If NO → Exit in <5 sec<br/>- Output: files_added=true/false"]

            Consolidate["CONSOLIDATE<br/>- Check: Complete day ready?<br/>- If YES → Convert to Parquet<br/>- If NO → Exit in <5 sec<br/>- Output: files_added=true/false"]

            Embed["EMBED<br/>- Check: Unembedded decisions?<br/>- If YES → Generate embeddings<br/>- If NO → Exit in <5 sec<br/>- Output: files_added=true/false"]
        end

        Lock --> Collect
        Lock --> Consolidate
        Lock --> Embed

        Collect -.->|async| Consolidate
        Consolidate -.->|async| Embed
        Embed -.->|async| DependCheck{Any files added?}

        DependCheck -->|YES| Catalog["CATALOG<br/>- Rebuild manifest<br/>- Output: catalog_updated=true/false"]
        DependCheck -->|NO| Skip["⏭️ SKIP CATALOG"]

        Catalog --> DashCheck{Catalog Updated?}
        DashCheck -->|YES| Dashboard["DASHBOARD-CACHE<br/>- Regenerate cache"]
        DashCheck -->|NO| SkipDash["⏭️ SKIP DASHBOARD"]

        style Collect fill:#51cf66
        style Consolidate fill:#51cf66
        style Embed fill:#51cf66
        style Catalog fill:#4dabf7
        style Dashboard fill:#b197fc
        style Skip fill:#868e96
        style SkipDash fill:#868e96
    end

    Benefits["✅ BENEFITS:<br/>- Global lock prevents workflow overlap<br/>- All 3 jobs run simultaneously<br/>- Each job is self-aware (checks for work)<br/>- Idle pipeline: <20 seconds<br/>- Active pipeline: <25 minutes<br/>- Catalog only runs if needed<br/>- Dashboard only updates when necessary"]

    style Benefits fill:#e0f2e0
```

## Time-Sliced Parallel Execution (Key Innovation)

```mermaid
graph TD
    subgraph "Cycle 1 (t=0:00-0:10)"
        C1A["t=0:00 COLLECT starts<br/>Has work? YES"]
        C1B["t=0:00-0:08<br/>Download & upload<br/>8 minutes of work"]
        C1C["t=0:08 Exit<br/>files_added=true"]

        C1A --> C1B --> C1C

        CO1A["t=0:00 CONSOLIDATE starts<br/>Has work? NO"]
        CO1B["t=0:00-0:05<br/>Check yesterday<br/>Not complete yet"]
        CO1C["t=0:05 Exit<br/>files_added=false"]

        CO1A --> CO1B --> CO1C

        E1A["t=0:00 EMBED starts<br/>Has work? NO"]
        E1B["t=0:00-0:03<br/>No unembedded decisions"]
        E1C["t=0:03 Exit<br/>files_added=false"]

        E1A --> E1B --> E1C

        CAT1["t=0:08-0:10<br/>CATALOG runs<br/>(files_added=true)<br/>Finishes in 2 min"]
    end

    subgraph "Cycle 2 (t=0:05 queued, starts t=0:10)"
        C2A["t=0:10 COLLECT starts<br/>Has work? YES<br/>(more data available)"]
        C2B["t=0:10-0:17<br/>Download & upload<br/>7 minutes of work"]
        C2C["t=0:17 Exit<br/>files_added=true"]

        C2A --> C2B --> C2C

        CO2A["t=0:10 CONSOLIDATE starts<br/>Has work? YES<br/>(yesterday now complete!)"]
        CO2B["t=0:10-0:19<br/>Convert ZIPs → Parquet<br/>9 minutes of work"]
        CO2C["t=0:19 Exit<br/>files_added=true"]

        CO2A --> CO2B --> CO2C

        E2A["t=0:10 EMBED starts<br/>Has work? YES<br/>(new decisions ready)"]
        E2B["t=0:10-0:14<br/>Generate embeddings<br/>4 minutes of work"]
        E2C["t=0:14 Exit<br/>files_added=true"]

        E2A --> E2B --> E2C

        CAT2["t=0:19-0:25<br/>CATALOG runs<br/>(files_added=true)<br/>Finishes in 6 min"]
    end

    C1C -.->|waited in queue| C2A
    CO1C -.->|waited in queue| CO2A
    E1C -.->|waited in queue| E2A

    CAT1 -.->|Cycle 1 complete<br/>by t=0:10| C2A
    CAT2 -.->|Cycle 2 complete<br/>by t=0:25| Next["Cycle 3<br/>queued at t=0:15<br/>starts t=0:25"]

    style C1C fill:#51cf66
    style CO2C fill:#51cf66
    style E2C fill:#51cf66
    style CAT1 fill:#4dabf7
    style CAT2 fill:#4dabf7
    style Next fill:#a5e3ff
```

**Key Pattern**:
- Jobs exit in <10 min, REGARDLESS of remaining work
- Next cycle (5 min later if available), job runs AGAIN with fresh opportunity
- Consolidation gets turn once Collect added enough ZIPs
- Embedding gets turn once Consolidation created Parquet files
- **Over time**: Entire backlog processed incrementally

---

## Job Execution Timeline (Original)

```mermaid
timeline
    title Workflow Execution Timeline (Ideal)

    section "t=0s: Workflow Starts"
        ALL THREE JOBS START IN PARALLEL

    section "t=0-5s: FAST PATH (Check for work)"
        COLLECT checks DJEN API (✅ Quick)
        CONSOLIDATE checks IA for complete days (✅ Quick)
        EMBED checks for unembedded decisions (✅ Quick)

    section "Case A: NO work needed (Idle)"
        All 3 jobs exit with files_added=false
        CATALOG is SKIPPED
        DASHBOARD is SKIPPED
        TOTAL TIME: 5-20 seconds

    section "Case B: COLLECT has work"
        COLLECT downloads ZIPs (10-30 sec)
        CONSOLIDATE finishes early (5 sec)
        EMBED finishes early (5 sec)
        CONSOLIDATE sets files_added=true
        CATALOG RUNS (indexes new ZIPs)
        DASHBOARD UPDATES
        TOTAL TIME: ~2-5 minutes

    section "Case C: All jobs have work"
        COLLECT downloads (20 sec)
        CONSOLIDATE converts to Parquet (10 min)
        EMBED generates embeddings (15 min)
        All set files_added=true
        CATALOG RUNS (15 min)
        DASHBOARD UPDATES (30 sec)
        TOTAL TIME: ~20-25 minutes
```

## Job Decision Logic (Each Job) - With 10-Minute Exit

```mermaid
flowchart TD
    Start["Job Starts<br/>(Every 5 min in same workflow)"]
    StartTime["Set: deadline = now + 10 minutes"]

    subgraph "CHECK PHASE (<5 seconds)"
        Check["Does this job have work?<br/>(Job-specific logic)"]
    end

    subgraph "WORK PHASE (if needed)"
        Work["Process 1 item/batch<br/>Upload to IA"]
        TimeCheck{Time check:<br/>now() <<br/>deadline?}
        MoreWork{More work<br/>available?}
    end

    subgraph "EXIT PHASE"
        NoWork["No work found<br/>files_added=false"]
        PartialExit["Processed some items<br/>More work remains<br/>files_added=true"]
        CompleteExit["Processed all items<br/>All work done<br/>files_added=true"]
        Done["Exit successfully"]
    end

    Start --> StartTime
    StartTime --> Check
    Check -->|NO work| NoWork
    Check -->|YES work| Work

    Work --> TimeCheck
    TimeCheck -->|Time expired| PartialExit
    TimeCheck -->|Time OK| MoreWork

    MoreWork -->|YES| Work
    MoreWork -->|NO| CompleteExit

    NoWork --> Done
    PartialExit --> Done
    CompleteExit --> Done

    style Check fill:#fff3bf
    style Work fill:#a5e3ff
    style Upload fill:#a5e3ff
    style TimeCheck fill:#fff3bf
    style MoreWork fill:#fff3bf
    style NoWork fill:#ffd43b
    style PartialExit fill:#51cf66
    style CompleteExit fill:#51cf66
    style Done fill:#51cf66
```

**Critical**: Each job has a **10-minute deadline** and exits regardless of remaining work. This allows other jobs to run on next cycle.

## Consolidate Job Logic (Detailed)

```mermaid
flowchart TD
    Start["CONSOLIDATE Starts"]

    subgraph "DETECTION PHASE"
        Scan["Scan Internet Archive<br/>for recent dates"]
        Check1{Does date D<br/>have complete<br/>ZIPs?<br/>All 91 tribunals?}
        Check2{Does date D<br/>already have<br/>Parquet files?}
    end

    subgraph "DECISION"
        Decision{"Ready to<br/>consolidate?"}
    end

    subgraph "WORK PHASE"
        Download["Download ZIPs from IA"]
        Convert["Convert to Parquet<br/>using DuckDB/Ibis"]
        UploadPQ["Upload Parquet to IA"]
        SetTrue["files_added=true"]
    end

    subgraph "EXIT PHASE"
        SetFalse["files_added=false"]
        Exit["Exit in <5 sec"]
    end

    Start --> Scan
    Scan --> Check1
    Check1 -->|NO: Incomplete| SetFalse
    Check1 -->|YES| Check2
    Check2 -->|YES: Already done| SetFalse
    Check2 -->|NO: Ready!| Decision
    Decision -->|YES| Download
    Download --> Convert
    Convert --> UploadPQ
    UploadPQ --> SetTrue
    SetFalse --> Exit
    SetTrue --> Exit

    style Start fill:#fff3bf
    style Scan fill:#fff3bf
    style Check1 fill:#fff3bf
    style Check2 fill:#fff3bf
    style Decision fill:#fff3bf
    style Download fill:#a5e3ff
    style Convert fill:#a5e3ff
    style UploadPQ fill:#a5e3ff
    style SetTrue fill:#51cf66
    style SetFalse fill:#ffd43b
    style Exit fill:#51cf66
```

## Catalog Conditional Trigger

```mermaid
flowchart TD
    AllJobsDone["All 3 jobs complete<br/>(COLLECT, CONSOLIDATE, EMBED)"]

    Check{"Any job<br/>has<br/>files_added=true?"}

    subgraph "Case: Files were added"
        Catalog["CATALOG job runs<br/>- Rebuilds manifest.parquet<br/>- Scans all IA items<br/>- Sets catalog_updated=true/false"]
        DashCheck{"CATALOG<br/>catalog_updated?"}
        Dashboard["DASHBOARD job runs<br/>- Regenerates cache"]
    end

    subgraph "Case: No files added"
        Skip["CATALOG SKIPPED<br/>DASHBOARD SKIPPED<br/>Exit in <20 sec total"]
    end

    AllJobsDone --> Check
    Check -->|NO| Skip
    Check -->|YES| Catalog
    Catalog --> DashCheck
    DashCheck -->|YES| Dashboard
    DashCheck -->|NO| SkipDash["DASHBOARD SKIPPED"]

    style AllJobsDone fill:#a5e3ff
    style Check fill:#fff3bf
    style Catalog fill:#4dabf7
    style Dashboard fill:#b197fc
    style Skip fill:#868e96
    style SkipDash fill:#868e96
    style DashCheck fill:#fff3bf
```

## Current vs Desired - Side by Side

```mermaid
graph LR
    subgraph "CURRENT (BROKEN)"
        A["❌ Collect<br/>Every 5 min<br/>lock: pipeline-collect<br/>takes 30s or timeout"]
        B["❌ Consolidate<br/>Every 10 min<br/>lock: pipeline-consolidate<br/>takes 19-20 min"]
        C["❌ Embed<br/>Every 60 min<br/>lock: pipeline-embed<br/>blocked by others"]
        D["❌ Catalog<br/>Every 24h<br/>lock: none<br/>always rebuilds"]

        A -.->|blocked| B
        B -.->|blocked| C
        C -.->|blocks| D
    end

    subgraph "DESIRED (FIXED)"
        E["✅ Collect<br/>Every 5 min<br/>GLOBAL lock<br/>PARALLEL<br/><5 sec if idle"]
        F["✅ Consolidate<br/>Every 5 min<br/>GLOBAL lock<br/>PARALLEL<br/><5 sec if idle"]
        G["✅ Embed<br/>Every 5 min<br/>GLOBAL lock<br/>PARALLEL<br/><5 sec if idle"]
        H["✅ Catalog<br/>CONDITIONAL<br/>After collect/consolidate/embed<br/>Only if files_added=true"]

        E -->|parallel| F
        F -->|parallel| G
        G -->|outputs| H
    end

    style A fill:#ff6b6b
    style B fill:#ff6b6b
    style C fill:#ff6b6b
    style D fill:#ffa94d
    style E fill:#51cf66
    style F fill:#51cf66
    style G fill:#51cf66
    style H fill:#4dabf7
```

## Implementation Plan Summary

### Phase 1: Fix Workflow YAML
- [ ] Add global concurrency lock: `group: pipeline-global`
- [ ] Schedule: Every 5 minutes (continuous harvest)
- [ ] Set job timeout: 15 minutes (10 min work + 5 min buffer)
- [ ] All 3 jobs run in parallel (no sequential dependencies)
- [ ] Add job outputs for `files_added=true/false` flag
- [ ] Make CATALOG conditionally run based on outputs
- [ ] Make DASHBOARD-CACHE conditionally run based on catalog outputs

### Phase 2: Update Python Scripts - ADD 10-MINUTE DEADLINE
- [ ] **collect.py**:
  - Add `--deadline 10m` parameter
  - Check: New data exists? If no → exit in <5 sec
  - Work loop: Download → Upload, check deadline each iteration
  - Exit when deadline reached (even if more data available)
  - Output: `files_added=true/false` to GITHUB_OUTPUT

- [ ] **consolidate.py**:
  - Add `--deadline 10m` parameter
  - Check: Complete day ready? If no → exit in <5 sec
  - Work loop: Download ZIP → Convert → Upload Parquet, check deadline
  - Exit when deadline reached (even if more days available)
  - Output: `files_added=true/false` to GITHUB_OUTPUT

- [ ] **embed.py**:
  - Add `--deadline 10m` parameter
  - Check: Unembedded decisions exist? If no → exit in <5 sec
  - Work loop: Embed batch, check deadline
  - Exit when deadline reached (even if more decisions available)
  - Output: `files_added=true/false` to GITHUB_OUTPUT

### Phase 3: Add Conditional Triggers
- [ ] CATALOG: `if: needs.collect.outputs.files_added == 'true' || needs.consolidate.outputs.files_added == 'true' || needs.embed.outputs.files_added == 'true'`
- [ ] DASHBOARD: `if: needs.catalog.outputs.catalog_updated == 'true'`

### Phase 4: Testing & Validation
- [ ] Test all 3 jobs reach 10-minute deadline and exit cleanly
- [ ] Verify files_added outputs are set correctly
- [ ] Verify CATALOG only runs when needed
- [ ] Monitor continuous cycles for 24 hours
- [ ] Verify backlog gradually decreases over time
- [ ] Validate no data loss from early exits
