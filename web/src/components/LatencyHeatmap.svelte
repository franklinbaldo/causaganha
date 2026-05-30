<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import MonthPicker from './MonthPicker.svelte';
  import { completedItemsStore } from '../lib/completedItemsStore.svelte';
  import {
    buildCatalogAttentionCards,
    countCoverageFilters,
    filterCoverageDays,
    getDayStatusLabel,
    summarizeCatalogDay,
    type CoverageFilter,
  } from '../lib/coverageInsights';

  onMount(() => completedItemsStore.load());

  // Svelte transitions are JS-driven, so the global CSS reduced-motion rule
  // does not reach them. Read the OS preference and zero the duration.
  const prefersReducedMotion = typeof window !== 'undefined'
    && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  const fadeDuration = prefersReducedMotion ? 0 : 120;

  const _now = new Date();
  let selectedYear  = $state(_now.getUTCFullYear());
  let selectedMonth = $state(_now.getUTCMonth());
  let coverageFilter = $state<CoverageFilter>('all');
  let expandedDate = $state<string | null>(null);

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
  let monthDays = $derived.by(() => {
    if (!data) return [];
    const prefix = `djen-${selectedYear}-${String(selectedMonth + 1).padStart(2, '0')}-`;
    return Object.keys(data)
      .filter(k => k.startsWith(prefix))
      .sort((a, b) => b.localeCompare(a))
      .map(key => summarizeCatalogDay(key, data[key]));
  });

  let filterCounts = $derived(countCoverageFilters(monthDays));
  let displayDates = $derived(filterCoverageDays(monthDays, coverageFilter));
  let attentionCards = $derived(buildCatalogAttentionCards([...monthDays].sort((a, b) => a.date.localeCompare(b.date))));

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

  function setFilter(filter: CoverageFilter) {
    coverageFilter = filter;
    expandedDate = null;
  }

  function toggleDate(date: string) {
    expandedDate = expandedDate === date ? null : date;
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
    <p>Tempo para download e backup do ZIP de cada tribunal, com status textual e drilldown para lacunas de cobertura.</p>
  </header>

  <MonthPicker bind:selectedYear bind:selectedMonth {monthSummaries} />

  <ul class="auto-grid-sm" aria-label="Legenda">
    <li><span class="legend-dot cell-success" aria-hidden="true"></span> ✓ &lt; 5s rápido</li>
    <li><span class="legend-dot cell-warning" aria-hidden="true"></span> ⚠ 5–20s atenção</li>
    <li><span class="legend-dot cell-error" aria-hidden="true"></span> ⏱ &gt; 20s lento</li>
    <li><span class="legend-dot cell-empty" aria-hidden="true"></span> ○ ausente/pendente</li>
  </ul>

  {#if loading}
    <p aria-busy="true"><progress></progress></p>
  {:else if error}
    <mark data-tone="error">Erro ao carregar dados: {error}</mark>
  {:else}
    {#key `${selectedYear}-${selectedMonth}`}
      <div transition:fade={{ duration: fadeDuration }}>
        <section class="auto-grid" aria-label="Cartões de atenção da latência">
          {#each attentionCards as card}
            <article class="attention-card" data-tone={card.tone}>
              <header>
                <strong><span aria-hidden="true">{card.icon}</span> {card.title}</strong>
                <span class="badge" data-tone={card.tone}>{card.summary}</span>
              </header>
              <p>{card.impact}</p>
              <p>{card.cause}</p>
              <p><strong>{card.action}</strong></p>
            </article>
          {/each}
        </section>

        <fieldset class="filter-pills" aria-label="Filtro rápido de dias da latência">
          <legend>Filtrar dias</legend>
          <button type="button" class:contrast={coverageFilter === 'all'} onclick={() => setFilter('all')}>Todos ({filterCounts.all})</button>
          <button type="button" class:contrast={coverageFilter === 'failed'} onclick={() => setFilter('failed')}>⚠ Dias com falha ({filterCounts.failed})</button>
          <button type="button" class:contrast={coverageFilter === 'complete'} onclick={() => setFilter('complete')}>✓ Dias completos ({filterCounts.complete})</button>
          <button type="button" class:contrast={coverageFilter === 'no-data'} onclick={() => setFilter('no-data')}>○ Dias sem dados ({filterCounts.noData})</button>
        </fieldset>

        <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Data</th>
              {#each TRIBUNALS as tribunal}
                <th title={tribunal}>{tribunal}</th>
              {/each}
            </tr>
          </thead>
          <tbody>
            {#each displayDates as day}
              {@const dateStr = day.key}
              {@const dayData = data?.[dateStr]}
              {@const latencies = dayData?.latencies || {}}
              {@const coletados = dayData?.tribunais_coletados || []}
              {@const ausentes  = dayData?.tribunais_ausentes  || []}
              <tr>
                <td>
                  <button type="button" class="link-button" aria-expanded={expandedDate === day.date} onclick={() => toggleDate(day.date)}>
                    {day.date}
                  </button>
                  <br />
                  <span class="badge" data-tone={day.status === 'complete' ? 'success' : day.status === 'failed' ? 'warning' : 'info'}>{getDayStatusLabel(day)}</span>
                </td>
                {#each TRIBUNALS as tribunal}
                  {@const isColetado = coletados.includes(tribunal)}
                  {@const isAusente  = ausentes.includes(tribunal)}
                  {@const status  = isColetado ? 'coletado' : isAusente ? 'ausente' : 'pendente'}
                  {@const latency = latencies[tribunal] ?? null}
                  <td>
                    <div
                      class="heatmap-cell {isColetado ? getLatencyColor(latency) : 'cell-empty'}"
                      role="button"
                      tabindex="0"
                      title="{tribunal} em {dateStr.replace('djen-', '')}: {isColetado && latency !== null ? `Latência: ${formatDuration(latency)}` : isAusente ? 'Tribunal ausente nesta data' : 'Sem dado de latência'}"
                      aria-label="{tribunal} em {dateStr.replace('djen-', '')}: {isColetado ? formatDuration(latency) : status}"
                    >
                      <span class="sr-only">{isColetado ? formatDuration(latency) : status}</span>
                    </div>
                  </td>
                {/each}
              </tr>
              {#if expandedDate === day.date}
                <tr>
                  <td colspan={TRIBUNALS.length + 1}>
                    <div class="drilldown-panel">
                      <strong>Tribunais faltantes em {day.date}</strong>
                      <p>Impacto: células vazias podem significar ausência oficial, pendência de coleta ou latência ainda não registrada.</p>
                      {#if day.missingTribunals.length > 0}
                        <ul class="chip-list">
                          {#each day.missingTribunals as tribunal}
                            <li><span class="badge" data-tone="warning">⚠ {tribunal}</span></li>
                          {/each}
                        </ul>
                      {:else}
                        <p>Nenhum tribunal ausente registrado para esta data.</p>
                      {/if}
                    </div>
                  </td>
                </tr>
              {/if}
            {/each}
            {#if displayDates.length === 0}
              <tr>
                <td colspan={TRIBUNALS.length + 1} class="empty-state">
                  Sem dados para este filtro neste mês.
                </td>
              </tr>
            {/if}
          </tbody>
        </table>
        </div>
      </div>
    {/key}
  {/if}
</article>
