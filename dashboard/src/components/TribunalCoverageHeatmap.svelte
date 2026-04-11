<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { getCoverageColorClass } from '../lib/colorUtils';
  import MonthPicker from './MonthPicker.svelte';
  import { completedItemsStore } from '../lib/completedItemsStore.svelte';

  onMount(() => completedItemsStore.load());

  const _now = new Date();
  let selectedYear  = $state(_now.getUTCFullYear());
  let selectedMonth = $state(_now.getUTCMonth());

  const data    = $derived(completedItemsStore.data);
  const loading = $derived(completedItemsStore.loading);
  const error   = $derived(completedItemsStore.error);

  // "YYYY-MM" → average daily coverage (0-1) for month picker badges
  let monthSummaries = $derived.by((): Record<string, number> => {
    if (!data) return {};
    const acc: Record<string, { sum: number; count: number }> = {};
    for (const key of Object.keys(data)) {
      const cleaned = key.replace('djen-', ''); // "YYYY-MM-DD"
      const monthKey = cleaned.substring(0, 7);  // "YYYY-MM"
      const item = data[key];
      const pct = Math.min(1, (item.tribunal_count || 0) / 91);
      if (!acc[monthKey]) acc[monthKey] = { sum: 0, count: 0 };
      acc[monthKey].sum += pct;
      acc[monthKey].count += 1;
    }
    const result: Record<string, number> = {};
    for (const [k, v] of Object.entries(acc)) {
      result[k] = v.count > 0 ? v.sum / v.count : 0;
    }
    return result;
  });

  // Days belonging to the selected month, sorted ascending
  let displayDates = $derived.by(() => {
    if (!data) return [];
    const prefix = `djen-${selectedYear}-${String(selectedMonth + 1).padStart(2, '0')}-`;
    return Object.keys(data)
      .filter(k => k.startsWith(prefix))
      .sort((a, b) => a.localeCompare(b));
  });

</script>

<div class="card">
  <div class="card-body">
    <h3 class="card-title">Cobertura do Catálogo</h3>

    <MonthPicker bind:selectedYear bind:selectedMonth {monthSummaries} />

    {#if loading}
      <div class="loading-msg">Carregando dados de cobertura...</div>
    {:else if error}
      <div class="text-error">Erro: {error}</div>
    {:else}
      {#key `${selectedYear}-${selectedMonth}`}
        <div transition:fade={{ duration: 120 }}>
          <div class="table-responsive">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Data</th>
                  <th>ZIPs Coletados</th>
                  <th>Ausentes</th>
                  <th>Cobertura %</th>
                  <th>Barra</th>
                </tr>
              </thead>
              <tbody>
                {#each displayDates as dateKey}
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
                    <td class={total === 0 ? undefined : textClass}>{pct.toFixed(1)}%</td>
                    <td>
                      <div
                        class="progress-bar-track"
                        role="progressbar"
                        aria-valuenow={Math.min(100, pct)}
                        aria-valuemin={0}
                        aria-valuemax={100}
                        aria-label="{displayDate}: {pct.toFixed(1)}% cobertura"
                      >
                        <div
                          class="progress-bar-fill {total === 0 ? '' : bgClass}"
                          style="width:{Math.min(100, pct)}%"
                        ></div>
                      </div>
                    </td>
                  </tr>
                {/each}
                {#if displayDates.length === 0}
                  <tr><td colspan="5" class="empty-msg">Sem dados para este mês.</td></tr>
                {/if}
              </tbody>
            </table>
          </div>
        </div>
      {/key}
    {/if}
  </div>
</div>

<style>
  .loading-msg { padding: 1rem 0; opacity: 0.6; font-size: var(--font-size-sm); }
  .text-error  { color: var(--color-error); }
  .empty-msg   { padding: 1rem 0; opacity: 0.5; text-align: center; }

  .table-responsive { overflow-x: auto; margin-top: 1rem; }

  .data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--font-size-sm);
    white-space: nowrap;
  }
  .data-table th, .data-table td { padding: 0.5rem 0.75rem; text-align: left; }
  .data-table thead th { font-weight: 600; border-bottom: 1px solid var(--color-base-300); }
  .data-table tbody tr:nth-child(even) { background: var(--color-base-200, rgba(0,0,0,0.03)); }
  .hoverable-row:hover { background: var(--color-base-200, rgba(0,0,0,0.05)); }

  .progress-bar-track {
    width: 100%; height: 0.5rem;
    background: var(--color-base-200, rgba(0,0,0,0.05));
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
