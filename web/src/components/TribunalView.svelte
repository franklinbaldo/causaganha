<script lang="ts">
  import { TRIBUNAL_GROUPS } from '../lib/tribunais';
  import { useDashboardWithPolling } from '../lib/useDashboard.svelte';
  import QueryProvider from './QueryProvider.svelte';
  import TribunalCard from './TribunalCard.svelte';

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

  const dashboard = useDashboardWithPolling();

  const pipeline = $derived(dashboard.data?.cacheData?.today?.pipeline ?? initialPipeline);
  const progressByYear = $derived(dashboard.data?.progressByYear ?? initialProgressByYear);
  const volume = $derived(dashboard.data?.volume ?? initialVolume);
  const iaSnapshot = $derived(dashboard.data?.iaSnapshot ?? initialIaSnapshot);

  let query = $state('');

  const snap = $derived(iaSnapshot?.summary);
  const totalZips = $derived(snap?.total_zips || pipeline?.total_zips || 0);
  const totalGB = $derived(snap?.total_size_gb || volume?.total_gb || 0);
  const tribunalsWithData = $derived(snap?.tribunals_with_data || 0);
  const latestDate = $derived(snap?.latest_collection_date);
  const snapshotAge = $derived(iaSnapshot?.generated_at);

  const snapshotItems = $derived(iaSnapshot?.items || {});
  const snapshotByYear = $derived(iaSnapshot?.by_year || {});

  const BASE = import.meta.env.BASE_URL;
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

<QueryProvider>
<div>
  <!-- Archive Progress -->
  <article>
    <header>
      <h2>Progresso do Arquivo</h2>
        {#if latestDate}
          <span class="meta-text">
            Última coleta: {latestDate}
            {#if snapshotAge}
              <span> · {new Date(snapshotAge).toLocaleString('pt-BR', { timeZone: 'UTC', hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' })} UTC</span>
            {/if}
          </span>
        {/if}
    </header>

    <!-- Quick Stats -->
    <dl class="auto-grid-sm">
      <div>
        <dt class="stat-label">ZIPs no IA</dt>
        <dd class="stat-value">{totalZips.toLocaleString('pt-BR')}</dd>
      </div>
      <div>
        <dt class="stat-label">Volume</dt>
        <dd class="stat-value">{totalGB.toFixed(1)}<small>GB</small></dd>
      </div>
      <div>
        <dt class="stat-label">Tribunais</dt>
        <dd class="stat-value">{tribunalsWithData}<small>/ {snap?.tribunals_total || 96}</small></dd>
      </div>
      <div>
        <dt class="stat-label">Itens no IA</dt>
        <dd class="stat-value">{snap?.total_items || 0}</dd>
      </div>
    </dl>
  </article>

  <!-- Progress by Year -->
  {#if Object.keys(snapshotByYear).length > 0}
    <article>
      <header>
        <strong>ZIPs por Ano</strong>
        <small class="meta-text">Internet Archive</small>
      </header>
      <div class="auto-grid-sm">
        {#each Object.entries(snapshotByYear).sort(([a], [b]) => b.localeCompare(a)) as [year, d]}
          <article>
            <header>
              <strong class="small-text">{year}</strong>
              <code>{(d as any).zip_count.toLocaleString('pt-BR')}</code>
            </header>
            <small class="meta-text">
              {(d as any).tribunals_with_data} / {(d as any).tribunals_total} tribunais
            </small>
          </article>
        {/each}
      </div>
    </article>
  {:else if progressByYear && Object.keys(progressByYear).length > 0}
    <article>
      <header>
        <strong>Progresso por Ano</strong>
      </header>
      <div class="auto-grid-sm">
        {#each Object.entries(progressByYear).sort(([a], [b]) => b.localeCompare(a)) as [year, d]}
          {@const pct = (d as any).pct || 0}
          <article>
            <header>
              <strong class="small-text">{year}</strong>
              <strong>{pct.toFixed(1)}%</strong>
            </header>
            <progress value={Math.round(Math.min(100, pct))} max="100" aria-label={`Progresso de coleta para o ano ${year}`}></progress>
            <small>
              <span>{(d as any).zips || 0} ZIPs</span>
              · <span>{(d as any).days_consolidated || 0} consolidados</span>
              · <span>{(d as any).unique_days || 0} / {(d as any).weekdays || 0} dias</span>
            </small>
          </article>
        {/each}
      </div>
    </article>
  {/if}

  <!-- Tribunal Filter -->
  <search>
    <label for="tribunal-filter">Filtrar tribunais</label>
    <div>
      <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16" aria-hidden="true"><path fill-rule="evenodd" d="M9.965 11.026a5 5 0 1 1 1.06-1.06l2.755 2.754a.75.75 0 1 1-1.06 1.06l-2.755-2.754ZM10.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z" clip-rule="evenodd" /></svg>
      <input
        id="tribunal-filter" type="search"
        value={query}
        oninput={(event) => query = (event.target as HTMLInputElement).value}
        onkeydown={(event) => {
          if (event.key === 'Escape') query = '';
        }}
        placeholder="Busque por sigla ou nome (ex.: tjsp, trf1, stj)"
        aria-label="Filtrar tribunais por sigla ou nome"
      />
      {#if query}
        <button type="button" class="secondary outline" onclick={() => query = ''} aria-label="Limpar filtro">Limpar</button>
      {/if}
    </div>
  </search>

  <!-- Tribunal Groups -->
  {#if filteredGroups.length === 0}
    <div class="empty-state">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
      <p class="no-margin">Nenhum tribunal encontrado para "{query.trim()}". Tente buscar por outra sigla ou nome.</p>
    </div>
  {:else}
    {#each filteredGroups as group}
      <section>
        <header>
          <h3>{group.name}</h3>
          <small class="meta-text">{group.tribunals.length} tribunais</small>
        </header>
        <div class="auto-grid">
          {#each group.tribunals as t}
            {@const stats = getTribunalStats(t)}
            <TribunalCard
              tribunal={t}
              href={`${baseUrl}publicacoes/${t.toLowerCase()}`}
              hasData={stats.hasData}
              totalZips={stats.totalZips}
              latestDate={stats.latestDate}
            />
          {/each}
        </div>
      </section>
    {/each}
  {/if}
</div>
</QueryProvider>
