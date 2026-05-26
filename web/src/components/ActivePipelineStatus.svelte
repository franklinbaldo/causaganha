<script lang="ts">
  import { createQuery, setQueryClientContext } from '@tanstack/svelte-query';
  import QueryProvider from './QueryProvider.svelte';
  import { QUERY_KEYS } from '../lib/queryKeys';
  import { fetchWithRetry } from '../lib/fetchData';
  import { getQueryClient } from '../lib/queryClient';

  // Initialize context for this island (must run during component init, before createQuery)
  setQueryClientContext(getQueryClient());

  interface TodayData {
    tribunal_status: Record<string, { status: string; last_update: string | null; doc_count: number }>;
  }

  interface RunData {
    status: string;
  }

  interface RunsResponse {
    runs: RunData[];
  }

  const BASE_URL = import.meta.env.BASE_URL;
  const CACHE_RUNS_URL = `${BASE_URL.replace(/\/$/, '')}/cache/runs.json`;
  const CACHE_TODAY_URL = `${BASE_URL.replace(/\/$/, '')}/cache/today.json`;

  const runsQuery = createQuery(() => ({
    queryKey: QUERY_KEYS.pipelineRuns,
    queryFn: async () => {
      const res = await fetchWithRetry(CACHE_RUNS_URL + '?t=' + Date.now());
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json() as Promise<RunsResponse>;
    },
    refetchInterval: 60_000,
    staleTime: 50_000,
  }));

  const todayQuery = createQuery(() => ({
    queryKey: QUERY_KEYS.pipelineToday,
    queryFn: async () => {
      const res = await fetchWithRetry(CACHE_TODAY_URL + '?t=' + Date.now());
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json() as Promise<TodayData>;
    },
    refetchInterval: 60_000,
    staleTime: 50_000,
  }));

  const isPipelineActive = $derived.by(() => {
    const runs = runsQuery.data?.runs;
    return Array.isArray(runs) && runs.length > 0 && runs[0].status === 'in_progress';
  });

  const activeTribunal = $derived.by(() => {
    const status = todayQuery.data?.tribunal_status;
    if (!status) return null;
    for (const [code, info] of Object.entries(status)) {
      if (info.status === 'pending' || info.status === 'running') return code;
    }
    return null;
  });

  const error = $derived(runsQuery.isError || todayQuery.isError);
</script>

<QueryProvider>
  <div class="active-pipeline-widget">
    {#if error}
      <span class="status-text muted">Falha ao carregar status</span>
    {:else if isPipelineActive}
      <div class="live-indicator">
        <span class="cg-pulse dot-pulse"></span>
        <strong class="status-text live">Ao Vivo</strong>
      </div>
      {#if activeTribunal}
        <mark class="tribunal-badge">{activeTribunal}</mark>
      {/if}
    {:else}
      <span class="status-text muted">Sistema Ocioso</span>
    {/if}
  </div>
</QueryProvider>
