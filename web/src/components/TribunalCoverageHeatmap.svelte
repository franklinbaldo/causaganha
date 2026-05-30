<script lang="ts">
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import { getCoverageColorClass } from '../lib/colorUtils';
  import {
    buildCatalogAttentionCards,
    countCoverageFilters,
    filterCoverageDays,
    getDayStatusLabel,
    summarizeCatalogDay,
    type CoverageFilter,
  } from '../lib/coverageInsights';
  import MonthPicker from './MonthPicker.svelte';
  import { completedItemsStore } from '../lib/completedItemsStore.svelte';

  onMount(() => completedItemsStore.load());

  const _now = new Date();
  let selectedYear  = $state(_now.getUTCFullYear());
  let selectedMonth = $state(_now.getUTCMonth());
  let coverageFilter = $state<CoverageFilter>('all');
  let expandedDate = $state<string | null>(null);

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
  let monthDays = $derived.by(() => {
    if (!data) return [];
    const prefix = `djen-${selectedYear}-${String(selectedMonth + 1).padStart(2, '0')}-`;
    return Object.keys(data)
      .filter(k => k.startsWith(prefix))
      .sort((a, b) => a.localeCompare(b))
      .map(key => summarizeCatalogDay(key, data[key]));
  });

  let filterCounts = $derived(countCoverageFilters(monthDays));
  let displayDates = $derived(filterCoverageDays(monthDays, coverageFilter));
  let attentionCards = $derived(buildCatalogAttentionCards(monthDays));

  function setFilter(filter: CoverageFilter) {
    coverageFilter = filter;
    expandedDate = null;
  }

  function toggleDate(date: string) {
    expandedDate = expandedDate === date ? null : date;
  }
</script>

<article>
  <h3>Cobertura do Catálogo</h3>
  <p>
    Acompanhe falhas por dia sem depender só da cor: cada linha mostra status textual,
    contagens e uma lista dos tribunais ausentes quando houver lacuna.
  </p>

  <MonthPicker bind:selectedYear bind:selectedMonth {monthSummaries} />

  {#if loading}
    <p role="status" aria-live="polite" aria-busy="true" data-tone="info">Carregando dados de cobertura...</p>
  {:else if error}
    <p data-tone="error">Erro: {error}</p>
  {:else}
    {#key `${selectedYear}-${selectedMonth}`}
      <div transition:fade={{ duration: 120 }}>
        <section class="auto-grid" aria-label="Cartões de atenção da cobertura">
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

        <fieldset class="filter-pills" aria-label="Filtro rápido de cobertura">
          <legend>Filtrar dias</legend>
          <button type="button" class:contrast={coverageFilter === 'all'} onclick={() => setFilter('all')}>
            Todos ({filterCounts.all})
          </button>
          <button type="button" class:contrast={coverageFilter === 'failed'} onclick={() => setFilter('failed')}>
            ⚠ Dias com falha ({filterCounts.failed})
          </button>
          <button type="button" class:contrast={coverageFilter === 'complete'} onclick={() => setFilter('complete')}>
            ✓ Dias completos ({filterCounts.complete})
          </button>
          <button type="button" class:contrast={coverageFilter === 'no-data'} onclick={() => setFilter('no-data')}>
            ○ Dias sem dados ({filterCounts.noData})
          </button>
        </fieldset>

        <div class="table-wrap">
          <table class="striped">
            <thead>
              <tr>
                <th>Data</th>
                <th>Status</th>
                <th>ZIPs Coletados</th>
                <th>Ausentes</th>
                <th>Cobertura %</th>
                <th>Barra</th>
                <th>Drilldown</th>
              </tr>
            </thead>
            <tbody>
              {#each displayDates as day}
                {@const colorClasses = getCoverageColorClass(day.pct)}
                {@const textClass = colorClasses.split(' ')[0]}
                <tr>
                  <td>{day.date}</td>
                  <td><span class="badge" data-tone={day.status === 'complete' ? 'success' : day.status === 'failed' ? 'warning' : 'info'}>{getDayStatusLabel(day)}</span></td>
                  <td>{day.collected}</td>
                  <td>{day.absent}</td>
                  <td class={day.total === 0 ? undefined : textClass}>{day.pct.toFixed(1)}%</td>
                  <td>
                    <progress
                      value={Math.min(100, day.pct)}
                      max="100"
                      aria-label="{day.date}: {day.pct.toFixed(1)}% cobertura; {day.absent} tribunais ausentes"
                    ></progress>
                  </td>
                  <td>
                    <button
                      type="button"
                      class="outline secondary"
                      disabled={day.missingTribunals.length === 0}
                      aria-expanded={expandedDate === day.date}
                      onclick={() => toggleDate(day.date)}
                    >
                      Ver ausentes ({day.missingTribunals.length})
                    </button>
                  </td>
                </tr>
                {#if expandedDate === day.date}
                  <tr>
                    <td colspan="7">
                      <div class="drilldown-panel">
                        <strong>Tribunais ausentes em {day.date}</strong>
                        {#if day.missingTribunals.length > 0}
                          <p>Impacto: essas siglas podem não aparecer em buscas e agregações desta data.</p>
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
                <tr><td colspan="7" class="empty-state">Sem dados para este filtro neste mês.</td></tr>
              {/if}
            </tbody>
          </table>
        </div>
      </div>
    {/key}
  {/if}
</article>
