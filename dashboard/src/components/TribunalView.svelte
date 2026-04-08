<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { createDataRefresh } from '../lib/dataRefreshStore';
  import { TRIBUNAL_GROUPS } from '../lib/tribunais';

  let {
    initialPipeline,
    initialProgressByYear,
    initialVolume,
    initialIaSnapshot,
  } = $props<{
    initialPipeline: any;
    initialProgressByYear: Record<string, any> | null;
    initialVolume: any;
    initialIaSnapshot: any;
  }>();

  const store = createDataRefresh(null, null);
  onMount(() => store.start());
  onDestroy(() => store.stop());

  const pipeline = $derived($store.data?.cacheData?.today?.pipeline ?? initialPipeline);
  const progressByYear = $derived($store.data?.progressByYear ?? initialProgressByYear);
  const volume = $derived($store.data?.volume ?? initialVolume);
  const iaSnapshot = $derived($store.data?.iaSnapshot ?? initialIaSnapshot);

  let query = $state('');

  const snap = $derived(iaSnapshot?.summary);
  const totalZips = $derived(snap?.total_zips || pipeline?.total_zips || 0);
  const totalGB = $derived(snap?.total_size_gb || volume?.total_gb || 0);
  const tribunalsWithData = $derived(snap?.tribunals_with_data || 0);
  const latestDate = $derived(snap?.latest_collection_date);
  const snapshotAge = $derived(iaSnapshot?.generated_at);

  const snapshotItems = $derived(iaSnapshot?.items || {});
  const snapshotByYear = $derived(iaSnapshot?.by_year || {});

  const BASE = typeof import.meta !== 'undefined' ? (import.meta.env?.BASE_URL || '/causaganha/') : '/causaganha/';
  const baseUrl = BASE.endsWith('/') ? BASE : BASE + '/';

  const normalizedQuery = $derived(query.trim().toLowerCase());

  const filteredGroups = $derived(
    TRIBUNAL_GROUPS
      .map(group => ({
        ...group,
        tribunals: group.tribunals.filter(tribunal => {
          if (!normalizedQuery) return true;
          return tribunal.toLowerCase().includes(normalizedQuery);
        }),
      }))
      .filter(group => group.tribunals.length > 0)
  );

  function getTribunalStats(t: string) {
    let totalZips = 0;
    let latestDate: string | null = null;
    if (snapshotItems) {
      for (const item of Object.values(snapshotItems)) {
        if ((item as any).tribunal === t) {
          totalZips += (item as any).zip_count;
          if (!latestDate || (item as any).latest_date > latestDate) latestDate = (item as any).latest_date;
        }
      }
    }
    return { totalZips, latestDate, hasData: totalZips > 0 };
  }
</script>

<div>
  <!-- Archive Progress -->
  <div class="card bg-base-100 shadow-sm border border-base-300 mb-16"><div class="card-body">
    <header class="pb-4 border-b border-base-300 mb-6">
      <div class="flex justify-between items-baseline flex-wrap gap-2 items-center">
        <h2 class="mb-0 text-2xl">Progresso do Arquivo</h2>
        {#if latestDate}
          <span class="text-xs opacity-50">
            Última coleta: {latestDate}
            {#if snapshotAge}
              <span> · {new Date(snapshotAge).toLocaleString('pt-BR', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })} UTC</span>
            {/if}
          </span>
        {/if}
      </div>
    </header>

    <!-- Quick Stats -->
    <div class="stats stats-vertical lg:stats-horizontal shadow-sm w-full mb-6">
      <div class="stat text-center">
        <div class="stat-value text-info">{totalZips.toLocaleString()}</div>
        <p class="stat-title mt-2">ZIPs no IA</p>
      </div>
      <div class="stat text-center">
        <div class="stat-value text-warning">{totalGB.toFixed(1)}<small class="font-medium" style="font-size: 0.4em; margin-left: 0.15em">GB</small></div>
        <p class="stat-title mt-2">Volume</p>
      </div>
      <div class="stat text-center">
        <div class="stat-value text-success">{tribunalsWithData}<small class="font-normal opacity-50 text-base-content" style="font-size: 0.4em; margin-left: 0.15em">/ {snap?.tribunals_total || 96}</small></div>
        <p class="stat-title mt-2">Tribunais</p>
      </div>
      <div class="stat text-center">
        <div class="stat-value text-primary">{snap?.total_items || 0}</div>
        <p class="stat-title mt-2">Itens no IA</p>
      </div>
    </div>
  </div></div>

  <!-- Progress by Year -->
  {#if Object.keys(snapshotByYear).length > 0}
    <div class="card bg-base-100 shadow-sm border border-base-300 mb-16"><div class="card-body">
      <header class="pb-4 border-b border-base-300 mb-6 flex justify-between items-baseline">
        <strong>ZIPs por Ano</strong>
        <small class="opacity-50 text-xs">Internet Archive</small>
      </header>
      <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 1rem">
        {#each Object.entries(snapshotByYear).sort(([a], [b]) => b.localeCompare(a)) as [year, d]}
          <div class="card bg-base-100 shadow-sm border border-base-300 mb-0"><div class="card-body p-4">
            <div class="flex justify-between items-baseline mb-2">
              <strong class="text-sm">{year}</strong>
              <span class="font-mono text-sm font-bold">{(d as any).zip_count.toLocaleString()}</span>
            </div>
            <small class="opacity-50 text-xs">
              {(d as any).tribunals_with_data} / {(d as any).tribunals_total} tribunais
            </small>
          </div></div>
        {/each}
      </div>
    </div></div>
  {:else if progressByYear && Object.keys(progressByYear).length > 0}
    <div class="card bg-base-100 shadow-sm border border-base-300 mb-16"><div class="card-body">
      <header class="pb-4 border-b border-base-300 mb-6">
        <strong>Progresso por Ano</strong>
      </header>
      <div>
        {#each Object.entries(progressByYear).sort(([a], [b]) => b.localeCompare(a)) as [year, d]}
          {@const pct = (d as any).pct || 0}
          <div class="mb-6">
            <div class="flex justify-between items-baseline mb-2">
              <strong class="text-sm">{year}</strong>
              <span class="font-mono text-sm font-semibold">{pct.toFixed(1)}%</span>
            </div>
            <progress class="progress progress-primary" value={Math.round(Math.min(100, pct))} max="100" aria-label={`Progresso de coleta para o ano ${year}`}></progress>
            <div class="opacity-50 text-xs flex gap-4 mt-2">
              <span>{(d as any).zips || 0} ZIPs</span>
              <span>{(d as any).days_consolidated || 0} consolidados</span>
              <span>{(d as any).unique_days || 0} / {(d as any).weekdays || 0} dias</span>
            </div>
          </div>
        {/each}
      </div>
    </div></div>
  {/if}

  <!-- Tribunal Filter -->
  <div class="mb-6 mt-10">
    <label for="tribunal-filter" class="text-sm font-medium opacity-70 mb-2 block">
      Filtrar tribunais
    </label>
    <label class="input input-bordered flex items-center gap-2 max-w-lg">
      <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16" class="opacity-50"><path fill-rule="evenodd" d="M9.965 11.026a5 5 0 1 1 1.06-1.06l2.755 2.754a.75.75 0 1 1-1.06 1.06l-2.755-2.754ZM10.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z" clip-rule="evenodd" /></svg>
      <input
        id="tribunal-filter" type="search"
        class="grow"
        value={query}
        oninput={(event) => query = (event.target as HTMLInputElement).value}
        onkeydown={(event) => {
          if (event.key === 'Escape') query = '';
        }}
        placeholder="Busque por sigla ou nome (ex.: tjsp, trf1, stj)"
        aria-label="Filtrar tribunais por sigla ou nome"
      />
      {#if query}
        <span class="badge badge-info badge-sm cursor-pointer" onclick={() => query = ''}>Limpar</span>
      {/if}
    </label>
  </div>

  <!-- Tribunal Groups -->
  {#if filteredGroups.length === 0}
    <div class="empty-state">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
      <p class="mb-0">Nenhum tribunal encontrado para "{query.trim()}". Tente buscar por outra sigla ou nome.</p>
    </div>
  {:else}
    {#each filteredGroups as group}
      <section class="mb-16">
        <div class="mb-6 pb-4 border-b border-base-300">
          <h3 class="text-xl mb-2" style="margin-bottom: 0.25rem">{group.name}</h3>
          <small class="opacity-50 text-xs">{group.tribunals.length} tribunais</small>
        </div>
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 1rem">
          {#each group.tribunals as t}
            {@const stats = getTribunalStats(t)}
            <a
              href={`${baseUrl}publicacoes/${t.toLowerCase()}`}
              style="text-decoration: none; color: inherit">
              <div class="card bg-base-100 shadow-sm border border-base-300 hover:shadow-md transition-shadow h-100"><div class="card-body p-4">
                <div class="flex justify-between items-baseline items-center mb-2">
                  <strong class="text-sm">{t}</strong>
                  <span class={stats.hasData ? "badge badge-success badge-sm" : "badge badge-error badge-sm"}>{stats.hasData ? "Online" : "Offline"}</span>
                </div>
                <div class="text-xs opacity-70 mb-2">
                  {#if stats.hasData}
                    {stats.totalZips.toLocaleString()} publicações
                  {:else}
                    Sem dados processados
                  {/if}
                  {#if stats.latestDate}
                    <span class="block mt-1 opacity-70">Última: {stats.latestDate}</span>
                  {/if}
                </div>
                <progress class={`progress w-full ${stats.hasData ? 'progress-success' : 'progress-error'}`} value={stats.hasData ? 100 : 0} max="100"></progress>
              </div></div>
            </a>
          {/each}
        </div>
      </section>
    {/each}
  {/if}
</div>
