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
      const dayTotal = (item.tribunal_count || 0) + (item.absent_count || 0);
      const pct = dayTotal > 0 ? Math.min(1, (item.tribunal_count || 0) / dayTotal) : 0;
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

<article>
  <h3>Cobertura do Catálogo</h3>

  <MonthPicker bind:selectedYear bind:selectedMonth {monthSummaries} />

  {#if loading}
    <p role="status" aria-live="polite" aria-busy="true" data-tone="info">Carregando dados de cobertura...</p>
  {:else if error}
    <p data-tone="error">Erro: {error}</p>
  {:else}
    {#key `${selectedYear}-${selectedMonth}`}
      <div transition:fade={{ duration: 120 }}>
        <div class="table-wrap">
          <table class="striped">
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
                {@const pct = total > 0 ? Math.min(100, (tribunalCount / total) * 100) : 0}
                {@const displayDate = dateKey.replace('djen-', '')}
                {@const colorClasses = getCoverageColorClass(pct)}
                {@const textClass = colorClasses.split(' ')[0]}
                {@const bgClass = colorClasses.split(' ')[1]}
                <tr>
                  <td>{displayDate}</td>
                  <td>{tribunalCount}</td>
                  <td>{absentCount}</td>
                  <td class={total === 0 ? undefined : textClass}>{pct.toFixed(1)}%</td>
                  <td>
                    <progress
                      value={Math.min(100, pct)}
                      max="100"
                      aria-label="{displayDate}: {pct.toFixed(1)}% cobertura"
                    ></progress>
                  </td>
                </tr>
              {/each}
              {#if displayDates.length === 0}
                <tr><td colspan="5" class="empty-state">Sem dados para este mês.</td></tr>
              {/if}
            </tbody>
          </table>
        </div>
      </div>
    {/key}
  {/if}
</article>
