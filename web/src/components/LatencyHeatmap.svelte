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
    if (duration_s === null) return 'bg-base-200';
    if (duration_s < 5)     return 'bg-success';
    if (duration_s <= 20)   return 'bg-warning';
    return 'bg-error';
  }

  function getLatencyClass(duration_s: number | null): string {
    return duration_s === null ? '' : 'text-white opacity-90';
  }

  function formatDuration(duration_s: number | null): string {
    return duration_s === null ? 'N/A' : duration_s.toFixed(1) + 's';
  }
</script>

<div class="card bg-base-100 shadow-xl border border-base-200">
  <div class="card-body p-4 md:p-6">
    <div class="mb-4">
      <h2 class="card-title text-xl flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        Latência de Coleta
      </h2>
      <p class="text-sm text-base-content/70">Tempo para download e backup do ZIP de cada tribunal.</p>
    </div>

    <MonthPicker bind:selectedYear bind:selectedMonth {monthSummaries} />

    <div class="flex gap-4 text-xs font-medium mt-4 mb-2">
      <div class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-success inline-block"></span> &lt; 5s</div>
      <div class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-warning inline-block"></span> 5-20s</div>
      <div class="flex items-center gap-1"><span class="w-3 h-3 rounded-sm bg-error inline-block"></span> &gt; 20s</div>
    </div>

    {#if loading}
      <div class="flex justify-center items-center py-12">
        <span class="loading loading-spinner loading-lg text-primary" aria-busy="true"></span>
      </div>
    {:else if error}
      <div class="alert alert-error shadow-sm my-4">
        <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <span>Erro ao carregar dados: {error}</span>
      </div>
    {:else}
      {#key `${selectedYear}-${selectedMonth}`}
        <div class="overflow-x-auto w-full pb-4" transition:fade={{ duration: fadeDuration }}>
          <table class="table table-xs w-full min-w-max">
            <thead>
              <tr>
                <th class="sticky left-0 bg-base-100 z-10 opacity-70 w-24">Data</th>
                {#each TRIBUNALS as tribunal}
                  <th class="font-mono text-center text-[10px] w-6 p-0 opacity-70" title={tribunal}>
                    <div class="-rotate-45 translate-y-2 translate-x-1 w-6">{tribunal}</div>
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
                  <td class="sticky left-0 bg-base-100 z-10 font-mono text-[10px] whitespace-nowrap">
                    {dateStr.replace('djen-', '')}
                  </td>
                  {#each TRIBUNALS as tribunal}
                    {@const isColetado = coletados.includes(tribunal)}
                    {@const isAusente  = ausentes.includes(tribunal)}
                    {@const status  = isColetado ? 'coletado' : isAusente ? 'ausente' : 'pendente'}
                    {@const latency = latencies[tribunal] ?? null}
                    <td class="p-0.5 min-w-[24px]">
                      <CellTooltip
                        date={dateStr.replace('djen-', '')}
                        tribunal={tribunal}
                        {status}
                        fileName={isColetado ? `djen-${dateStr.replace('djen-', '')}-${tribunal}.zip` : undefined}
                        detail={isColetado && latency !== null ? `Latency: ${formatDuration(latency)}` : undefined}
                      >
                        <div
                          class="w-6 h-6 rounded-sm mx-auto transition-all duration-200 hover:ring-2 hover:ring-primary/50 hover:scale-110 cursor-pointer {isColetado ? getLatencyColor(latency) : 'bg-base-200'} {getLatencyClass(latency)}"
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
                  <td colspan={TRIBUNALS.length + 1} class="text-center py-4 opacity-50 text-sm">
                    Sem dados para este mês.
                  </td>
                </tr>
              {/if}
            </tbody>
          </table>
        </div>
      {/key}
    {/if}
  </div>
</div>
