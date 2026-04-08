<script lang="ts">
  import { onMount } from 'svelte';
  import { getCoverageColorClass } from '../lib/colorUtils';

  let data: Record<string, any> | null = $state(null);
  let loading = $state(true);
  let error: string | null = $state(null);

  // Initialize period from URL query param if available, defaulting to '90d'
  let period = $state((() => {
    if (typeof window !== 'undefined') {
      const params = new URLSearchParams(window.location.search);
      const urlPeriod = params.get('period');
      if (['30d', '90d', '1a'].includes(urlPeriod ?? '')) {
        return urlPeriod!;
      }
    }
    return '90d';
  })());

  const daysMap: Record<string, number> = {
    '30d': 30,
    '90d': 90,
    '1a': 365,
  };

  const days = $derived(daysMap[period] || 90);

  const sortedDates = $derived(
    data ? Object.keys(data).sort((a, b) => b.localeCompare(a)) : []
  );

  const recent = $derived(sortedDates.slice(0, days));

  const periods = ['30d', '90d', '1a'] as const;

  function handlePeriodChange(newPeriod: string) {
    period = newPeriod;
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.set('period', newPeriod);
      window.history.replaceState({}, '', url.toString());
    }
  }

  onMount(() => {
    let isMounted = true;
    const fetchData = async () => {
      try {
        loading = true;
        const response = await fetch(
          `https://archive.org/download/causaganha-catalog/completed-items.json?t=${Date.now()}`
        );
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const json = await response.json();
        if (isMounted) {
          data = json.completed_items || {};
          error = null;
        }
      } catch (e: unknown) {
        if (isMounted) {
          const message = e instanceof Error ? e.message : String(e);
          console.error('Failed to fetch catalog completed-items.json:', e);
          error = message;
        }
      } finally {
        if (isMounted) loading = false;
      }
    };
    fetchData();
    return () => {
      isMounted = false;
    };
  });
</script>

<div class="card bg-base-100 shadow-sm border border-base-300">
  <div class="card-body">
    <div>
      <h3>Recent Catalog Coverage ({period})</h3>
      <div>
        {#each periods as p}
          <button
            onclick={() => handlePeriodChange(p)}
            class={period === p ? "btn" : "btn btn-secondary"}
          >
            {p}
          </button>
        {/each}
      </div>
    </div>

    {#if loading}
      <div>Loading coverage data...</div>
    {:else if error}
      <div class="text-error">Error: {error}</div>
    {:else}
      <div>
        <div class="table-responsive">
          <table class="table table-zebra table-sm whitespace-nowrap">
            <thead>
              <tr>
                <th>Date</th>
                <th>ZIPs Collected</th>
                <th>Absent</th>
                <th>Coverage %</th>
                <th>Visual Bar</th>
              </tr>
            </thead>
            <tbody>
              {#each recent as dateKey}
                {@const item = data![dateKey]}
                {@const tribunalCount = item.tribunal_count || 0}
                {@const absentCount = item.absent_count || 0}
                {@const total = tribunalCount + absentCount}
                {@const pct = Math.min(100, (tribunalCount / 91) * 100)}
                {@const displayDate = dateKey.replace('djen-', '')}
                {@const colorClasses = getCoverageColorClass(pct)}
                {@const textClass = colorClasses.split(' ')[0]}
                {@const bgClass = colorClasses.split(' ')[1]}
                <tr class="hover">
                  <td>{displayDate}</td>
                  <td>{tribunalCount}</td>
                  <td>{absentCount}</td>
                  <td class={total === 0 ? undefined : textClass}>
                    {pct.toFixed(1)}%
                  </td>
                  <td>
                    <div>
                      <div
                        class={total === 0 ? undefined : bgClass}
                        style="width: {Math.min(100, pct)}%"
                        title="{pct.toFixed(1)}% Coverage"
                      ></div>
                    </div>
                  </td>
                </tr>
              {/each}
              {#if recent.length === 0}
                <tr>
                  <td colspan="5">No data available in catalog.</td>
                </tr>
              {/if}
            </tbody>
          </table>
        </div>
      </div>
    {/if}
  </div>
</div>
