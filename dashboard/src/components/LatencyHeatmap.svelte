<script lang="ts">
  import { onMount } from 'svelte';
  import CellTooltip from './CellTooltip.svelte';

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

  const displayDates = $derived(sortedDates.slice(0, days));

  // Pre-define standard tribunals
  const TRIBUNALS = [
    "STF", "STJ", "TST", "TSE", "STM",
    "TRF1", "TRF2", "TRF3", "TRF4", "TRF5", "TRF6",
    "TJAC", "TJAL", "TJAM", "TJAP", "TJBA", "TJCE", "TJDFT",
    "TJES", "TJGO", "TJMA", "TJMG", "TJMS", "TJMT", "TJPA",
    "TJPB", "TJPE", "TJPI", "TJPR", "TJRJ", "TJRN", "TJRO",
    "TJRR", "TJRS", "TJSC", "TJSE", "TJSP", "TJMRS", "TJMSP",
    "PJeCor"
  ];

  function handlePeriodChange(newPeriod: string) {
    period = newPeriod;
    // Update URL query string
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
      } catch (e) {
        if (isMounted) {
          error = e instanceof Error ? e.message : 'Unknown error occurred';
          console.error('Error fetching completed items:', e);
        }
      } finally {
        if (isMounted) {
          loading = false;
        }
      }
    };
    fetchData();
    return () => {
      isMounted = false;
    };
  });

  function getLatencyColor(duration_s: number | null): string {
    if (duration_s === null) return 'bg-base-200'; // Default/No data
    if (duration_s < 5) return 'bg-success'; // Fast
    if (duration_s <= 20) return 'bg-warning'; // Medium
    return 'bg-error'; // Slow
  }

  function getLatencyClass(duration_s: number | null): string {
    if (duration_s === null) return '';
    return 'text-white opacity-90'; // better contrast if it's solid color
  }

  function formatDuration(duration_s: number | null): string {
    if (duration_s === null) return 'N/A';
    return duration_s.toFixed(1) + 's';
  }
</script>

<div class="card bg-base-100 shadow-xl border border-base-200">
  <div class="card-body p-4 md:p-6">
    <div class="flex justify-between items-center mb-4">
      <div>
        <h2 class="card-title text-xl flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-primary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Collection Latency
        </h2>
        <p class="text-sm text-base-content/70">Time taken to download and backup each tribunal's DJEN ZIP.</p>
      </div>


      <div class="flex gap-2">
        <div class="join">
          <button class="join-item btn btn-xs {period === '30d' ? 'btn-active' : ''}" onclick={() => handlePeriodChange('30d')}>30d</button>
          <button class="join-item btn btn-xs {period === '90d' ? 'btn-active' : ''}" onclick={() => handlePeriodChange('90d')}>90d</button>
          <button class="join-item btn btn-xs {period === '1a' ? 'btn-active' : ''}" onclick={() => handlePeriodChange('1a')}>1a</button>
        </div>
      </div>
    </div>

    <div class="flex gap-4 text-xs font-medium mb-4">
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
        <svg xmlns="http://www.w3.org/2000/svg" class="stroke-current shrink-0 h-6 w-6" fill="none" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
        <span>Error loading data: {error}</span>
      </div>
    {:else}
      <div class="overflow-x-auto w-full pb-4">
        <table class="table table-xs w-full min-w-max">
          <thead>
            <tr>
              <th class="sticky left-0 bg-base-100 z-10 opacity-70 w-24">Date</th>
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
              {@const ausentes = dayData?.tribunais_ausentes || []}
              <tr>
                <td class="sticky left-0 bg-base-100 z-10 font-mono text-[10px] whitespace-nowrap">
                  {dateStr.replace('djen-', '')}
                </td>
                {#each TRIBUNALS as tribunal}
                  {@const isColetado = coletados.includes(tribunal)}
                  {@const isAusente = ausentes.includes(tribunal)}
                  {@const status = isColetado ? 'coletado' : isAusente ? 'ausente' : 'pendente'}
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
                        aria-label="{tribunal} on {dateStr.replace('djen-', '')}: {isColetado ? formatDuration(latency) : status}"
                      ></div>
                    </CellTooltip>
                  </td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  </div>
</div>
