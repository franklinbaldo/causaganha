<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchWithRetry } from '../lib/fetchData';

  interface TodayData {
    tribunal_status: Record<string, { status: string; last_update: string | null; doc_count: number }>;
  }

  interface RunData {
    status: string;
  }

  interface RunsResponse {
    runs: RunData[];
  }

  let isPipelineActive = $state<boolean>(false);
  let activeTribunal = $state<string | null>(null);
  let error = $state<boolean>(false);
  let isMounted = $state<boolean>(false);

  // Need to ensure absolute path from root via BASE_URL
  const BASE_URL = import.meta.env?.BASE_URL || '/causaganha/';
  // In dev/preview, BASE_URL might be different, let's make sure we hit the correct static path.
  const CACHE_RUNS_URL = `${BASE_URL.replace(/\/$/, '')}/cache/runs.json`;
  const CACHE_TODAY_URL = `${BASE_URL.replace(/\/$/, '')}/cache/today.json`;

  const poll = async () => {
    if (!isMounted) return;
    try {
      const [runsRes, todayRes] = await Promise.all([
          fetchWithRetry(CACHE_RUNS_URL + '?t=' + Date.now()),
          fetchWithRetry(CACHE_TODAY_URL + '?t=' + Date.now()),
      ]);

      if (runsRes.ok && todayRes.ok) {
        const runsData: RunsResponse = await runsRes.json();
        const todayData: TodayData = await todayRes.json();

        // Determine if pipeline is active
        if (runsData.runs && runsData.runs.length > 0) {
          isPipelineActive = runsData.runs[0].status === 'in_progress';
        } else {
          isPipelineActive = false;
        }

        // Determine active tribunal: find any tribunal with status pending
        // Or if none are pending, but the pipeline is active, we just fallback or look for the most recently updated.
        // The instructions suggest looking for pending status as the active tribunal, or most recent timestamp.
        let foundPending = false;
        let mostRecentTribunal: string | null = null;
        let maxDocCount = -1; // Fallback to tribunal with most docs today, or we can just show generic active

        for (const [code, info] of Object.entries(todayData.tribunal_status)) {
          if (info.status === 'pending' || info.status === 'running') {
            activeTribunal = code;
            foundPending = true;
            break;
          }
        }

        if (!foundPending) {
           // If no pending but pipeline active, maybe processing something not in 'pending' status?
           // or we just show null. The widget will just show "Live" in this case.
           activeTribunal = null;
        }

        error = false;
      } else {
        error = true;
      }
    } catch (e) {
      error = true;
    }
  };

  onMount(() => {
    isMounted = true;
    poll();
    const interval = setInterval(poll, 60000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  });
</script>

<div class="active-pipeline-widget">
  {#if error}
    <span class="status-text muted">Falha ao carregar status</span>
  {:else if isPipelineActive}
    <div class="live-indicator">
      <span class="cg-pulse dot-pulse"></span>
      <span class="status-text font-bold text-success">Ao Vivo</span>
    </div>
    {#if activeTribunal}
      <span class="tribunal-badge badge badge-primary">{activeTribunal}</span>
    {/if}
  {:else}
    <span class="status-text muted">Sistema Ocioso</span>
  {/if}
</div>

<style>
  .active-pipeline-widget {
    display: flex;
    align-items: center;
    gap: var(--space-2);
    font-size: var(--font-size-sm);
    padding: var(--space-1) var(--space-2);
    border-radius: var(--radius-btn);
    background: var(--color-base-200);
    border: 1px solid var(--color-base-300);
  }

  .live-indicator {
    display: flex;
    align-items: center;
    gap: var(--space-1);
  }

  .dot-pulse {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: var(--color-success, #22c55e);
  }

  .status-text {
    font-weight: 500;
  }

  .font-bold {
    font-weight: 700;
  }

  .text-success {
    color: var(--color-success, #22c55e);
  }

  .muted {
    opacity: 0.6;
  }

  .tribunal-badge {
    font-size: var(--font-size-xs);
    font-weight: 600;
  }
</style>
