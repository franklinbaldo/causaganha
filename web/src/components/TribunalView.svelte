<script lang="ts">
  import { TRIBUNAL_GROUPS } from '../lib/tribunais';
  import { useDashboardWithPolling } from '../lib/useDashboard.svelte';
  import QueryProvider from './QueryProvider.svelte';

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

  function formatDate(iso: string): string {
    const [y, m, d] = iso.split('-');
    return `${d}/${m}/${y}`;
  }

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
    <div class="stats">
      <div class="stat">
        <div class="stat-value value-info">{totalZips.toLocaleString('pt-BR')}</div>
        <p class="stat-title">ZIPs no IA</p>
      </div>
      <div class="stat">
        <div class="stat-value value-warning">{totalGB.toFixed(1)}<small class="unit-suffix">GB</small></div>
        <p class="stat-title">Volume</p>
      </div>
      <div class="stat">
        <div class="stat-value value-success">{tribunalsWithData}<small class="fraction-suffix">/ {snap?.tribunals_total || 96}</small></div>
        <p class="stat-title">Tribunais</p>
      </div>
      <div class="stat">
        <div class="stat-value value-primary">{snap?.total_items || 0}</div>
        <p class="stat-title">Itens no IA</p>
      </div>
    </div>
  </article>

  <!-- Progress by Year -->
  {#if Object.keys(snapshotByYear).length > 0}
    <article>
      <header>
        <strong>ZIPs por Ano</strong>
        <small class="meta-text">Internet Archive</small>
      </header>
      <div class="tribunals-grid">
        {#each Object.entries(snapshotByYear).sort(([a], [b]) => b.localeCompare(a)) as [year, d]}
          <article class="year-card">
            <div class="year-row">
              <strong class="small-text">{year}</strong>
              <span class="mono-value">{(d as any).zip_count.toLocaleString('pt-BR')}</span>
            </div>
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
      <div>
        {#each Object.entries(progressByYear).sort(([a], [b]) => b.localeCompare(a)) as [year, d]}
          {@const pct = (d as any).pct || 0}
          <div class="year-progress-block">
            <div class="year-row">
              <strong class="small-text">{year}</strong>
              <span class="mono-value-semibold">{pct.toFixed(1)}%</span>
            </div>
            <progress class="progress-bar progress-primary" value={Math.round(Math.min(100, pct))} max="100" aria-label={`Progresso de coleta para o ano ${year}`}></progress>
            <div class="progress-details">
              <span>{(d as any).zips || 0} ZIPs</span>
              <span>{(d as any).days_consolidated || 0} consolidados</span>
              <span>{(d as any).unique_days || 0} / {(d as any).weekdays || 0} dias</span>
            </div>
          </div>
        {/each}
      </div>
    </article>
  {/if}

  <!-- Tribunal Filter -->
  <div class="filter-section">
    <label for="tribunal-filter" class="filter-label">
      Filtrar tribunais
    </label>
    <label class="search-input-wrapper">
      <svg width="16" height="16" fill="currentColor" viewBox="0 0 16 16" class="search-icon"><path fill-rule="evenodd" d="M9.965 11.026a5 5 0 1 1 1.06-1.06l2.755 2.754a.75.75 0 1 1-1.06 1.06l-2.755-2.754ZM10.5 7a3.5 3.5 0 1 1-7 0 3.5 3.5 0 0 1 7 0Z" clip-rule="evenodd" /></svg>
      <input
        id="tribunal-filter" type="search"
        class="search-input"
        value={query}
        oninput={(event) => query = (event.target as HTMLInputElement).value}
        onkeydown={(event) => {
          if (event.key === 'Escape') query = '';
        }}
        placeholder="Busque por sigla ou nome (ex.: tjsp, trf1, stj)"
        aria-label="Filtrar tribunais por sigla ou nome"
      />
      {#if query}
        <button type="button" class="clear-btn outline secondary" onclick={() => query = ''} aria-label="Limpar filtro">Limpar</button>
      {/if}
    </label>
  </div>

  <!-- Tribunal Groups -->
  {#if filteredGroups.length === 0}
    <div class="empty-state">
      <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" /></svg>
      <p class="no-margin">Nenhum tribunal encontrado para "{query.trim()}". Tente buscar por outra sigla ou nome.</p>
    </div>
  {:else}
    {#each filteredGroups as group}
      <section class="group-section">
        <div class="group-header">
          <h3 class="group-title">{group.name}</h3>
          <small class="meta-text">{group.tribunals.length} tribunais</small>
        </div>
        <div class="tribunals-grid">
          {#each group.tribunals as t}
            {@const stats = getTribunalStats(t)}
            <a
              href={`${baseUrl}publicacoes/${t.toLowerCase()}`}
              class="tribunal-link"
            >
            <article class="tribunal-card" class:offline={!stats.hasData}>
                <div class="tribunal-card-header">
                  <strong class="small-text">{t}</strong>
                  <mark data-tone={stats.hasData ? 'success' : 'error'}>
                    {stats.hasData ? "Online" : "Offline"}
                  </mark>
                </div>
                <div class="tribunal-card-meta">
                  {#if stats.hasData}
                    {stats.totalZips.toLocaleString('pt-BR')} publicações
                  {:else}
                    Sem dados processados
                  {/if}
                  {#if stats.latestDate}
                    <span class="latest-date">Última: {formatDate(stats.latestDate)}</span>
                  {/if}
                </div>
              </article>
            </a>
          {/each}
        </div>
      </section>
    {/each}
  {/if}
</div>
</QueryProvider>

<style>
  article > header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .year-card {
    padding: var(--pico-card-sectioning-background-color, 1rem);
  }

  /* Stats */
  .stats {
    display: flex;
    flex-direction: column;
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-box);
    box-shadow: var(--shadow-sm);
    overflow: hidden;
    width: 100%;
    margin-bottom: 1.5rem;
  }

  @media (min-width: 1024px) {
    .stats {
      flex-direction: row;
    }
  }

  .stat {
    padding: 1rem 1.5rem;
    flex: 1;
    text-align: center;
  }

  .stat-value {
    font-size: var(--font-size-2xl, 1.5rem);
    font-weight: 700;
  }

  .stat-title {
    margin-top: 0.5rem;
    opacity: 0.6;
    font-size: var(--font-size-sm);
  }

  .value-info {
    color: var(--color-info);
  }

  .value-warning {
    color: var(--color-warning);
  }

  .value-success {
    color: var(--color-success);
  }

  .value-primary {
    color: var(--color-primary);
  }

  .unit-suffix {
    font-size: 0.4em;
    font-weight: 500;
    margin-left: 0.15em;
  }

  .fraction-suffix {
    font-size: 0.4em;
    font-weight: 400;
    margin-left: 0.15em;
    opacity: 0.5;
    color: var(--color-base-content);
  }

  /* Tribunal card grid */
  .tribunals-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 10rem), 1fr));
    gap: 1rem;
  }

  /* Year rows */
  .year-row {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.5rem;
  }

  .mono-value {
    font-family: var(--font-mono);
    font-size: var(--font-size-sm);
    font-weight: 700;
  }

  .mono-value-semibold {
    font-family: var(--font-mono);
    font-size: var(--font-size-sm);
    font-weight: 600;
  }

  /* Progress bars */
  .progress-bar {
    width: 100%;
    height: 0.5rem;
    appearance: none;
    border-radius: var(--radius-full);
  }

  .progress-bar::-webkit-progress-bar {
    background: var(--color-base-300);
    border-radius: var(--radius-full);
  }

  .progress-primary::-webkit-progress-value {
    background: var(--color-primary);
    border-radius: var(--radius-full);
  }

  .year-progress-block {
    margin-bottom: 1.5rem;
  }

  .progress-details {
    opacity: 0.5;
    font-size: var(--font-size-xs);
    display: flex;
    gap: 1rem;
    margin-top: 0.5rem;
  }

  /* Filter section */
  .filter-section {
    margin-bottom: 1.5rem;
    margin-top: 2.5rem;
  }

  .filter-label {
    font-size: var(--font-size-sm);
    font-weight: 500;
    opacity: 0.7;
    margin-bottom: 0.5rem;
    display: block;
  }

  .search-input-wrapper {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    max-width: 32rem;
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-field);
    padding: 0.5rem 0.75rem;
    background: var(--color-base-100);
  }

  .search-icon {
    opacity: 0.5;
    flex-shrink: 0;
  }

  .search-input {
    flex: 1;
    border: none;
    outline: none;
    background: transparent;
    font-size: var(--font-size-sm);
    min-width: 0;
  }

  /* Clear filter button */
  .clear-btn {
    padding: 0.25rem 0.75rem;
    font-size: var(--font-size-xs);
  }

  /* Empty state */
  .empty-state {
    text-align: center;
    padding: 2rem;
    opacity: 0.6;
  }

  .empty-state svg {
    width: 3rem;
    height: 3rem;
    margin-bottom: 1rem;
  }

  /* Group sections */
  .group-section {
    margin-bottom: 4rem;
  }

  .group-header {
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px solid var(--color-base-300);
  }

  .group-title {
    font-size: var(--font-size-xl, 1.25rem);
    margin-bottom: 0.25rem;
  }

  /* Tribunal cards */
  .tribunal-link {
    display: block;
    height: 100%;
    text-decoration: none;
    color: inherit;
  }

  .tribunal-link:hover .tribunal-card {
    border-color: var(--color-accent);
    box-shadow: var(--shadow-md);
  }

  .tribunal-card {
    height: 100%;
    transition: border-color var(--transition-base), box-shadow var(--transition-base);
  }

  .tribunal-card.offline {
    opacity: 0.6;
  }

  .tribunal-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .tribunal-card-meta {
    font-size: var(--font-size-xs);
    opacity: 0.7;
  }

  .latest-date {
    display: block;
    margin-top: 0.25rem;
    opacity: 0.7;
  }
</style>
