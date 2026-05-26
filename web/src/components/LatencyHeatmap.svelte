<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import CellTooltip from './CellTooltip.svelte';
  import MonthPicker from './MonthPicker.svelte';
  import { completedItemsStore } from '../lib/completedItemsStore.svelte';

  onMount(() => completedItemsStore.load());

  // Svelte transitions are JS-driven, so the global CSS reduced-motion rule
  // does not reach them. Read the OS preference and zero the duration.
  const prefersReducedMotion = typeof window !== 'undefined'
    && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  const fadeDuration = prefersReducedMotion ? 0 : 120;

  const _now = new Date();
  let selectedYear  = $state(_now.getUTCFullYear());
  let selectedMonth = $state(_now.getUTCMonth());

  const data    = $derived(completedItemsStore.data);
  const loading = $derived(completedItemsStore.loading);
  const error   = $derived(completedItemsStore.error);

  // "YYYY-MM" → fraction of (tribunal, day) pairs where tribunal was collected
  let monthSummaries = $derived.by((): Record<string, number> => {
    if (!data) return {};
    const acc: Record<string, { collected: number; total: number }> = {};
    for (const key of Object.keys(data)) {
      const cleaned = key.replace('djen-', '');
      const monthKey = cleaned.substring(0, 7);
      const item = data[key];
      const coletados: string[] = item?.tribunais_coletados || [];
      const ausentes: string[]  = item?.tribunais_ausentes  || [];
      if (!acc[monthKey]) acc[monthKey] = { collected: 0, total: 0 };
      acc[monthKey].collected += coletados.length;
      acc[monthKey].total     += coletados.length + ausentes.length;
    }
    const result: Record<string, number> = {};
    for (const [k, v] of Object.entries(acc)) {
      result[k] = v.total > 0 ? v.collected / v.total : 0;
    }
    return result;
  });

  // Days of the selected month, sorted descending (most recent first)
  let displayDates = $derived.by(() => {
    if (!data) return [];
    const prefix = `djen-${selectedYear}-${String(selectedMonth + 1).padStart(2, '0')}-`;
    return Object.keys(data)
      .filter(k => k.startsWith(prefix))
      .sort((a, b) => b.localeCompare(a));
  });

  const TRIBUNALS = [
    'STF', 'STJ', 'TST', 'TSE', 'STM',
    'TRF1', 'TRF2', 'TRF3', 'TRF4', 'TRF5', 'TRF6',
    'TJAC', 'TJAL', 'TJAM', 'TJAP', 'TJBA', 'TJCE', 'TJDFT',
    'TJES', 'TJGO', 'TJMA', 'TJMG', 'TJMS', 'TJMT', 'TJPA',
    'TJPB', 'TJPE', 'TJPI', 'TJPR', 'TJRJ', 'TJRN', 'TJRO',
    'TJRR', 'TJRS', 'TJSC', 'TJSE', 'TJSP', 'TJMRS', 'TJMSP',
    'PJeCor',
  ];


  function getLatencyColor(duration_s: number | null): string {
    if (duration_s === null) return 'cell-empty';
    if (duration_s < 5)     return 'cell-success';
    if (duration_s <= 20)   return 'cell-warning';
    return 'cell-error';
  }

  function formatDuration(duration_s: number | null): string {
    return duration_s === null ? 'N/A' : duration_s.toFixed(1) + 's';
  }
</script>

<article>
  <header>
    <h2>
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      Latência de Coleta
    </h2>
    <p>Tempo para download e backup do ZIP de cada tribunal.</p>
  </header>

  <MonthPicker bind:selectedYear bind:selectedMonth {monthSummaries} />

  <ul class="legend">
    <li><span class="swatch cell-success"></span> &lt; 5s</li>
    <li><span class="swatch cell-warning"></span> 5–20s</li>
    <li><span class="swatch cell-error"></span> &gt; 20s</li>
  </ul>

  {#if loading}
    <div class="loading-wrap" aria-busy="true">
      <progress></progress>
    </div>
  {:else if error}
    <mark data-tone="error">Erro ao carregar dados: {error}</mark>
  {:else}
    {#key `${selectedYear}-${selectedMonth}`}
      <div class="table-wrap" transition:fade={{ duration: fadeDuration }}>
        <table class="heatmap-table">
          <thead>
            <tr>
              <th class="col-date">Data</th>
              {#each TRIBUNALS as tribunal}
                <th class="col-tribunal" title={tribunal}>
                  <div class="th-label">{tribunal}</div>
                </th>
              {/each}
            </tr>
          </thead>
          <tbody>
            {#each displayDates as dateStr}
              {@const dayData = data?.[dateStr]}
              {@const latencies = dayData?.latencies || {}}
              {@const coletados = dayData?.tribunais_coletados || []}
              {@const ausentes  = dayData?.tribunais_ausentes  || []}
              <tr>
                <td class="col-date cell-date-label">
                  {dateStr.replace('djen-', '')}
                </td>
                {#each TRIBUNALS as tribunal}
                  {@const isColetado = coletados.includes(tribunal)}
                  {@const isAusente  = ausentes.includes(tribunal)}
                  {@const status  = isColetado ? 'coletado' : isAusente ? 'ausente' : 'pendente'}
                  {@const latency = latencies[tribunal] ?? null}
                  <td class="cell-pad">
                    <CellTooltip
                      date={dateStr.replace('djen-', '')}
                      tribunal={tribunal}
                      {status}
                      fileName={isColetado ? `djen-${dateStr.replace('djen-', '')}-${tribunal}.zip` : undefined}
                      detail={isColetado && latency !== null ? `Latency: ${formatDuration(latency)}` : undefined}
                    >
                      <div
                        class="heatmap-cell {isColetado ? getLatencyColor(latency) : 'cell-empty'}"
                        role="button"
                        tabindex="0"
                        aria-label="{tribunal} em {dateStr.replace('djen-', '')}: {isColetado ? formatDuration(latency) : status}"
                      ></div>
                    </CellTooltip>
                  </td>
                {/each}
              </tr>
            {/each}
            {#if displayDates.length === 0}
              <tr>
                <td colspan={TRIBUNALS.length + 1} class="empty-row">
                  Sem dados para este mês.
                </td>
              </tr>
            {/if}
          </tbody>
        </table>
      </div>
    {/key}
  {/if}
</article>

<style>
  h2 {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.25rem;
    margin: 0;
  }

  h2 svg {
    flex-shrink: 0;
    color: var(--pico-primary);
  }

  header p {
    margin: 0.25rem 0 0;
    font-size: 0.875rem;
    color: var(--pico-muted-color);
  }

  /* Legend */
  .legend {
    display: flex;
    gap: 1rem;
    list-style: none;
    padding: 0;
    margin: 1rem 0 0.5rem;
    font-size: 0.75rem;
    font-weight: 600;
  }

  .legend li {
    display: flex;
    align-items: center;
    gap: 0.25rem;
  }

  .swatch {
    display: inline-block;
    width: 0.75rem;
    height: 0.75rem;
    border-radius: 2px;
  }

  /* Loading */
  .loading-wrap {
    display: flex;
    justify-content: center;
    padding: 3rem 0;
  }

  /* Table */
  .heatmap-table {
    width: 100%;
    min-width: max-content;
    border-collapse: collapse;
    font-size: 0.625rem;
  }

  .col-date {
    position: sticky;
    left: 0;
    background: var(--pico-card-background-color);
    z-index: 10;
    width: 6rem;
    opacity: 0.7;
  }

  .col-tribunal {
    font-family: monospace;
    text-align: center;
    width: 1.5rem;
    padding: 0;
    opacity: 0.7;
  }

  .th-label {
    transform: rotate(-45deg) translateY(0.5rem) translateX(0.25rem);
    width: 1.5rem;
    display: block;
  }

  .cell-date-label {
    font-family: monospace;
    white-space: nowrap;
    font-size: 0.625rem;
  }

  .cell-pad {
    padding: 0.125rem;
    min-width: 1.5rem;
  }

  /* Heatmap cells */
  .heatmap-cell {
    width: 1.5rem;
    height: 1.5rem;
    border-radius: 2px;
    margin: 0 auto;
    cursor: pointer;
    transition: transform 0.2s, box-shadow 0.2s;
  }

  .heatmap-cell:hover {
    transform: scale(1.1);
    box-shadow: 0 0 0 2px var(--pico-primary);
  }

  .cell-empty   { background: var(--pico-muted-border-color); }
  .cell-success { background: var(--pico-color-green-500, #22c55e); }
  .cell-warning { background: var(--pico-color-yellow-500, #eab308); }
  .cell-error   { background: var(--pico-color-red-500, #ef4444); }

  .empty-row {
    text-align: center;
    padding: 1rem;
    opacity: 0.5;
    font-size: 0.875rem;
  }
</style>
