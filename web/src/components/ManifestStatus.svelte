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

  function coverageTone(pct: number): string {
    if (pct >= 80) return 'success';
    if (pct >= 40) return 'warning';
    if (pct > 0) return 'error';
    return 'muted';
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
  <p aria-busy="true">Carregando manifesto...</p>
{:else if error}
  <aside role="alert" class="alert">Erro ao carregar manifesto: {error}</aside>
{:else if data}
  <div class="totals-grid">
    <article>
      <small>Total</small>
      <strong>{data.totals.total.toLocaleString('pt-BR')}</strong>
      <small>datas × tribunais</small>
    </article>
    <article>
      <small>No IA</small>
      <strong data-tone="success">{data.totals.uploaded.toLocaleString('pt-BR')}</strong>
      <small>{data.totals.coverage_pct}% cobertura</small>
    </article>
    <article>
      <small>Pendente</small>
      <strong data-tone="warning">{data.totals.available.toLocaleString('pt-BR')}</strong>
      <small>aguardando upload</small>
    </article>
    <article>
      <small>Ausente</small>
      <strong class="muted">{data.totals.absent.toLocaleString('pt-BR')}</strong>
      <small>sem publicação</small>
    </article>
    <article>
      <small>Desconhecido</small>
      <strong data-tone="error">{data.totals.unknown.toLocaleString('pt-BR')}</strong>
      <small>não verificado</small>
    </article>
  </div>

  <small class="updated-at">Atualizado: {new Date(data.generated_at).toLocaleString('pt-BR')}</small>

  <nav class="tab-nav" aria-label="Visualização">
    <button type="button" aria-pressed={view === 'tribunals'} onclick={() => view = 'tribunals'}>
      Por Tribunal ({data.tribunals.length})
    </button>
    <button type="button" aria-pressed={view === 'years'} onclick={() => view = 'years'}>
      Por Ano ({data.years.length})
    </button>
  </nav>

  {#if view === 'tribunals'}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th><button type="button" class="sort-btn" onclick={() => sortBy('tribunal')}>
              Tribunal {sortKey === 'tribunal' ? (sortAsc ? '▲' : '▼') : ''}
            </button></th>
            <th class="num"><button type="button" class="sort-btn" onclick={() => sortBy('uploaded')}>
              No IA {sortKey === 'uploaded' ? (sortAsc ? '▲' : '▼') : ''}
            </button></th>
            <th class="num"><button type="button" class="sort-btn" onclick={() => sortBy('absent')}>
              Ausente {sortKey === 'absent' ? (sortAsc ? '▲' : '▼') : ''}
            </button></th>
            <th class="num"><button type="button" class="sort-btn" onclick={() => sortBy('unknown')}>
              ? {sortKey === 'unknown' ? (sortAsc ? '▲' : '▼') : ''}
            </button></th>
            <th class="num"><button type="button" class="sort-btn" onclick={() => sortBy('coverage_pct')}>
              Cobertura {sortKey === 'coverage_pct' ? (sortAsc ? '▲' : '▼') : ''}
            </button></th>
            <th>Período</th>
          </tr>
        </thead>
        <tbody>
          {#each sortedTribunals as t}
            <tr>
              <td><strong>{t.tribunal}</strong></td>
              <td class="num mono">{t.uploaded}</td>
              <td class="num mono muted">{t.absent}</td>
              <td class="num mono" data-tone={t.unknown ? 'error' : undefined}>{t.unknown || ''}</td>
              <td class="num">
                <progress value={t.coverage_pct} max="100" data-tone={coverageTone(t.coverage_pct)}
                  aria-label="{t.tribunal}: {t.coverage_pct}%"></progress>
                <span data-tone={coverageTone(t.coverage_pct)}>{t.coverage_pct}%</span>
              </td>
              <td class="period">
                {#if t.earliest_upload}
                  {t.earliest_upload} → {t.latest_upload}
                {:else}
                  <span class="muted">—</span>
                {/if}
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {:else}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Ano</th>
            <th class="num">No IA</th>
            <th class="num">Ausente</th>
            <th class="num">Desconhecido</th>
            <th class="num">Total</th>
            <th class="num">Cobertura</th>
          </tr>
        </thead>
        <tbody>
          {#each data.years as y}
            <tr>
              <td><strong>{y.year}</strong></td>
              <td class="num mono" data-tone="success">{y.uploaded.toLocaleString('pt-BR')}</td>
              <td class="num mono muted">{y.absent.toLocaleString('pt-BR')}</td>
              <td class="num mono" data-tone="error">{y.unknown.toLocaleString('pt-BR')}</td>
              <td class="num mono">{y.total.toLocaleString('pt-BR')}</td>
              <td class="num">
                <progress value={y.coverage_pct} max="100" data-tone={coverageTone(y.coverage_pct)}
                  aria-label="{y.year}: {y.coverage_pct}%"></progress>
                <span data-tone={coverageTone(y.coverage_pct)}>{y.coverage_pct}%</span>
              </td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}
{/if}
