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

<div class="card">
  <div class="card-body">
    <div>
      <h3>Recent Catalog Coverage ({period})</h3>
      <div>
        {#each periods as p}
          <button
            onclick={() => handlePeriodChange(p)}
            class={period === p ? "period-btn period-btn-active" : "period-btn"}
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
          <table class="data-table">
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
                <tr class="hoverable-row">
                  <td>{displayDate}</td>
                  <td>{tribunalCount}</td>
                  <td>{absentCount}</td>
                  <td class={total === 0 ? undefined : textClass}>
                    {pct.toFixed(1)}%
                  </td>
                  <td>
                    <div class="progress-bar-track">
                      <div
                        class={`progress-bar-fill ${total === 0 ? '' : bgClass}`}
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

<style>
  .card {
    background: var(--color-base-100);
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-box);
  }

  .card-body {
    padding: var(--space-sm);
  }

  .period-btn {
    display: inline-flex;
    align-items: center;
    padding: 0.375rem 0.75rem;
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-btn);
    background: transparent;
    color: var(--color-base-content);
    cursor: pointer;
    transition: var(--transition-base);
    font-size: var(--font-size-sm);
  }

  .period-btn-active {
    background: var(--color-primary);
    color: var(--color-base-100);
    border-color: var(--color-primary);
  }

  .text-error {
    color: var(--color-error);
  }

  .table-responsive {
    overflow-x: auto;
  }

  .data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--font-size-sm);
    white-space: nowrap;
  }

  .data-table th,
  .data-table td {
    padding: 0.5rem 0.75rem;
    text-align: left;
  }

  .data-table thead th {
    font-weight: 600;
    border-bottom: 1px solid var(--color-base-300);
  }

  .data-table tbody tr:nth-child(even) {
    background: var(--color-base-200, rgba(0, 0, 0, 0.03));
  }

  .hoverable-row:hover {
    background: var(--color-base-200, rgba(0, 0, 0, 0.05));
  }

  .progress-bar-track {
    width: 100%;
    height: 0.5rem;
    background: var(--color-base-200, rgba(0, 0, 0, 0.05));
    border-radius: var(--radius-full);
    overflow: hidden;
  }

  .progress-bar-fill {
    height: 100%;
    border-radius: var(--radius-full);
    transition: width 0.3s ease;
    background: var(--color-primary);
  }
</style>
