<script lang="ts">
  const IA_BASE = 'https://archive.org/download/causaganha-dashboard';

  interface TribunalSummary {
    tribunal: string;
    uploaded: number;
    available: number;
    absent: number;
    unknown: number;
    total: number;
    coverage_pct: number;
    earliest_upload: string;
    latest_upload: string;
  }

  interface YearSummary {
    year: number;
    uploaded: number;
    available: number;
    absent: number;
    unknown: number;
    total: number;
    coverage_pct: number;
  }

  interface ManifestSummary {
    generated_at: string;
    totals: {
      uploaded: number;
      available: number;
      absent: number;
      unknown: number;
      total: number;
      coverage_pct: number;
    };
    tribunals: TribunalSummary[];
    years: YearSummary[];
  }

  let data: ManifestSummary | null = $state(null);
  let error: string | null = $state(null);
  let loading = $state(true);
  let sortKey: keyof TribunalSummary = $state('coverage_pct');
  let sortAsc = $state(false);
  let view: 'tribunals' | 'years' = $state('tribunals');

  let sortedTribunals = $derived(
    data?.tribunals.toSorted((a, b) => {
      const va = a[sortKey];
      const vb = b[sortKey];
      if (typeof va === 'number' && typeof vb === 'number') {
        return sortAsc ? va - vb : vb - va;
      }
      return sortAsc
        ? String(va).localeCompare(String(vb))
        : String(vb).localeCompare(String(va));
    }) || []
  );

  function sortBy(key: keyof TribunalSummary) {
    if (sortKey === key) {
      sortAsc = !sortAsc;
    } else {
      sortKey = key;
      sortAsc = key === 'tribunal';
    }
  }

  function coverageColor(pct: number): string {
    if (pct >= 80) return 'text-success';
    if (pct >= 40) return 'text-warning';
    if (pct > 0) return 'text-error';
    return 'text-base-content/30';
  }

  async function fetchSummary() {
    try {
      const resp = await fetch(`${IA_BASE}/manifest-summary.json`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      data = await resp.json();
    } catch (e: any) {
      error = e.message;
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    fetchSummary();
  });
</script>

{#if loading}
  <div class="flex justify-center p-8">
    <span class="loading loading-spinner loading-lg"></span>
  </div>
{:else if error}
  <div class="alert alert-error">Erro ao carregar manifesto: {error}</div>
{:else if data}
  <!-- Totals -->
  <div class="stats stats-vertical lg:stats-horizontal shadow w-full mb-6">
    <div class="stat">
      <div class="stat-title">Total</div>
      <div class="stat-value text-2xl">{data.totals.total.toLocaleString('pt-BR')}</div>
      <div class="stat-desc">datas x tribunais</div>
    </div>
    <div class="stat">
      <div class="stat-title">No IA</div>
      <div class="stat-value text-2xl text-success">{data.totals.uploaded.toLocaleString('pt-BR')}</div>
      <div class="stat-desc">{data.totals.coverage_pct}% cobertura</div>
    </div>
    <div class="stat">
      <div class="stat-title">Pendente</div>
      <div class="stat-value text-2xl text-warning">{data.totals.available.toLocaleString('pt-BR')}</div>
      <div class="stat-desc">aguardando upload</div>
    </div>
    <div class="stat">
      <div class="stat-title">Ausente</div>
      <div class="stat-value text-2xl text-base-content/50">{data.totals.absent.toLocaleString('pt-BR')}</div>
      <div class="stat-desc">sem publicação</div>
    </div>
    <div class="stat">
      <div class="stat-title">Desconhecido</div>
      <div class="stat-value text-2xl text-error">{data.totals.unknown.toLocaleString('pt-BR')}</div>
      <div class="stat-desc">não verificado</div>
    </div>
  </div>

  <div class="text-xs opacity-50 mb-4">
    Atualizado: {new Date(data.generated_at).toLocaleString('pt-BR')}
  </div>

  <!-- Tab selector -->
  <div role="tablist" class="tabs tabs-boxed mb-4">
    <button type="button" role="tab" aria-selected={view === 'tribunals'} class="tab" class:tab-active={view === 'tribunals'} onclick={() => view = 'tribunals'}>
      Por Tribunal ({data.tribunals.length})
    </button>
    <button type="button" role="tab" aria-selected={view === 'years'} class="tab" class:tab-active={view === 'years'} onclick={() => view = 'years'}>
      Por Ano ({data.years.length})
    </button>
  </div>

  {#if view === 'tribunals'}
    <div class="overflow-x-auto">
      <table class="table table-zebra table-sm w-full">
        <thead>
          <tr>
            <th class="cursor-pointer" onclick={() => sortBy('tribunal')}>
              Tribunal {sortKey === 'tribunal' ? (sortAsc ? '▲' : '▼') : ''}
            </th>
            <th class="cursor-pointer text-right" onclick={() => sortBy('uploaded')}>
              No IA {sortKey === 'uploaded' ? (sortAsc ? '▲' : '▼') : ''}
            </th>
            <th class="cursor-pointer text-right" onclick={() => sortBy('absent')}>
              Ausente {sortKey === 'absent' ? (sortAsc ? '▲' : '▼') : ''}
            </th>
            <th class="cursor-pointer text-right" onclick={() => sortBy('unknown')}>
              ? {sortKey === 'unknown' ? (sortAsc ? '▲' : '▼') : ''}
            </th>
            <th class="cursor-pointer text-right" onclick={() => sortBy('coverage_pct')}>
              Cobertura {sortKey === 'coverage_pct' ? (sortAsc ? '▲' : '▼') : ''}
            </th>
            <th>Período</th>
          </tr>
        </thead>
        <tbody>
          {#each sortedTribunals as t}
            <tr>
              <td class="font-bold">{t.tribunal}</td>
              <td class="text-right font-mono">{t.uploaded}</td>
              <td class="text-right font-mono text-base-content/50">{t.absent}</td>
              <td class="text-right font-mono text-error">{t.unknown || ''}</td>
              <td class="text-right">
                <div class="flex items-center justify-end gap-2">
                  <progress
                    class="progress w-20"
                    class:progress-success={t.coverage_pct >= 80}
                    class:progress-warning={t.coverage_pct >= 40 && t.coverage_pct < 80}
                    class:progress-error={t.coverage_pct > 0 && t.coverage_pct < 40}
                    value={t.coverage_pct}
                    max="100"
                  ></progress>
                  <span class="text-xs font-medium w-12 text-right {coverageColor(t.coverage_pct)}">
                    {t.coverage_pct}%
                  </span>
                </div>
              </td>
              <td class="text-xs opacity-70">
                {#if t.earliest_upload}
                  {t.earliest_upload} → {t.latest_upload}
                {:else}
                  <span class="opacity-30">—</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else}
    <div class="overflow-x-auto">
      <table class="table table-zebra table-sm w-full">
        <thead>
          <tr>
            <th>Ano</th>
            <th class="text-right">No IA</th>
            <th class="text-right">Ausente</th>
            <th class="text-right">Desconhecido</th>
            <th class="text-right">Total</th>
            <th class="text-right">Cobertura</th>
          </tr>
        </thead>
        <tbody>
          {#each data.years as y}
            <tr>
              <td class="font-bold">{y.year}</td>
              <td class="text-right font-mono text-success">{y.uploaded.toLocaleString('pt-BR')}</td>
              <td class="text-right font-mono text-base-content/50">{y.absent.toLocaleString('pt-BR')}</td>
              <td class="text-right font-mono text-error">{y.unknown.toLocaleString('pt-BR')}</td>
              <td class="text-right font-mono">{y.total.toLocaleString('pt-BR')}</td>
              <td class="text-right">
                <div class="flex items-center justify-end gap-2">
                  <progress
                    class="progress w-20"
                    class:progress-success={y.coverage_pct >= 80}
                    class:progress-warning={y.coverage_pct >= 40 && y.coverage_pct < 80}
                    class:progress-error={y.coverage_pct > 0 && y.coverage_pct < 40}
                    value={y.coverage_pct}
                    max="100"
                  ></progress>
                  <span class="text-xs font-medium w-12 text-right {coverageColor(y.coverage_pct)}">
                    {y.coverage_pct}%
                  </span>
                </div>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
{/if}
