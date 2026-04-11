import { createQuery, useQueryClient, setQueryClientContext } from '@tanstack/svelte-query';
import { QUERY_KEYS } from './queryKeys';
import { fetchAllData } from './fetchData';
import { getQueryClient } from './queryClient';

const IA_META_URL = 'https://archive.org/download/causaganha-dashboard/meta.json';

/**
 * Initializes the TanStack QueryClient context for the current Svelte island,
 * then provides the dashboard query with the "only refetch if meta.json changed"
 * optimization.
 *
 * Call this at the top of each island component's <script> block.
 * Because all islands share the singleton QueryClient, only one polling
 * interval runs per page regardless of how many islands call this function.
 */
export function useDashboardWithPolling() {
  // Initialize context for this island (must run during component init)
  setQueryClientContext(getQueryClient());

  const queryClient = useQueryClient();

  // Lightweight 3-min sentinel — fetches only meta.json
  const metaQuery = createQuery(() => ({
    queryKey: QUERY_KEYS.dashboardMeta,
    queryFn: async () => {
      const res = await fetch(IA_META_URL);
      if (!res.ok) throw new Error(`meta.json HTTP ${res.status}`);
      return res.json() as Promise<{ generated_at: string }>;
    },
    refetchInterval: 3 * 60 * 1000,
    staleTime: 0,
    select: (d: { generated_at: string }) => d.generated_at,
  }));

  let lastGeneratedAt = $state<string | null>(null);

  $effect(() => {
    const current = metaQuery.data;
    if (current && current !== lastGeneratedAt) {
      if (lastGeneratedAt !== null) {
        // New data available — invalidate so all dashboard consumers refetch
        queryClient.invalidateQueries({ queryKey: QUERY_KEYS.dashboard });
      }
      lastGeneratedAt = current;
    }
  });

  return createQuery(() => ({
    queryKey: QUERY_KEYS.dashboard,
    queryFn: fetchAllData,
    staleTime: 15_000,
    refetchInterval: false as const,
  }));
}
