<script lang="ts">
import { createQuery, useQueryClient, setQueryClientContext } from '@tanstack/svelte-query';
import { fetchAllTribunalMetadata, getExpectedDays, type TribunalMetadata } from '../lib/iaMetadataFetcher';
import { getCoverageColor } from '../lib/colorUtils';
import { isLeapYear } from '../lib/dateUtils';
import { QUERY_KEYS } from '../lib/queryKeys';
import { getQueryClient } from '../lib/queryClient';

// Initialize context for this island (must run during component init, before createQuery)
setQueryClientContext(getQueryClient());

const queryClient = useQueryClient();
const currentYear = new Date().getFullYear();
const YEARS = [currentYear - 2, currentYear - 1, currentYear];

let year = $state(currentYear);
let sortBy = $state('percentage');
let sortDir = $state('desc');

// When year changes, TanStack auto-creates a new query for the new key.
// Previously-fetched years are served instantly from cache (up to 30min TTL).
const coverageQuery = createQuery(() => ({
  queryKey: QUERY_KEYS.iaCoverage(year),
  queryFn: () => fetchAllTribunalMetadata(year, undefined, { useCache: false }),
  staleTime: 30 * 60 * 1000,
  gcTime: 35 * 60 * 1000,
}));

function handleForceRefresh() {
  queryClient.invalidateQueries({ queryKey: QUERY_KEYS.iaCoverage(year) });
}

function handleSort(field: string) {
  if (sortBy === field) {
    sortDir = sortDir === 'asc' ? 'desc' : 'asc';
  } else {
    sortBy = field;
    sortDir = field === 'tribunal' ? 'asc' : 'desc';
  }
}

const results = $derived(coverageQuery.data ?? []);
const loading = $derived(coverageQuery.isLoading || coverageQuery.isFetching);

const sorted = $derived.by(() => {
  return [...results].sort((a: TribunalMetadata, b: TribunalMetadata) => {
    let cmp = 0;
    if (sortBy === 'tribunal') {
      cmp = a.tribunal.localeCompare(b.tribunal);
    } else if (sortBy === 'percentage') {
      cmp = a.percentage - b.percentage;
    } else if (sortBy === 'fileCount') {
      cmp = a.fileCount - b.fileCount;
    } else if (sortBy === 'downloads') {
      cmp = (a.downloads || 0) - (b.downloads || 0);
    }
    return sortDir === 'asc' ? cmp : -cmp;
  });
});

const expectedDays = $derived(getExpectedDays(year));
const complete = $derived(results.filter((r: TribunalMetadata) => r.percentage >= 90).length);
const partial = $derived(results.filter((r: TribunalMetadata) => r.percentage >= 50 && r.percentage < 90).length);
const low = $derived(results.filter((r: TribunalMetadata) => r.percentage > 0 && r.percentage < 50).length);
const missing = $derived(results.filter((r: TribunalMetadata) => r.percentage === 0).length);

function sortIcon(field: string): string {
  if (sortBy !== field) return '';
  return sortDir === 'asc' ? ' ↑' : ' ↓';
}
</script>

<div>
  <!-- Header -->
  <div>
    <h3>
      Cobertura Anual no Internet Archive
    </h3>
    <div>
      <div>
        {#each YEARS as y}
          <button
            onclick={() => { year = y; }}
            class={year === y ? "year-btn year-btn-active" : "year-btn"}>
            {y}
          </button>
        {/each}
      </div>
      <button
        onclick={() => handleForceRefresh()}
        disabled={loading}
        title="Atualizar dados">
        Refresh
      </button>
    </div>
  </div>

  <!-- Loading indicator -->
  {#if loading}
    <div>
      Consultando Internet Archive...
    </div>
  {/if}

  <!-- Summary cards -->
  {#if results.length > 0}
    <div class="summary-grid">
      <div class="summary-card"><div class="summary-card-body">
        <div>{complete}</div>
        <small>&gt;90%</small>
      </div></div>
      <div class="summary-card"><div class="summary-card-body">
        <div>{partial}</div>
        <small>50-89%</small>
      </div></div>
      <div class="summary-card"><div class="summary-card-body">
        <div>{low}</div>
        <small>&lt;50%</small>
      </div></div>
      <div class="summary-card"><div class="summary-card-body">
        <div>{missing}</div>
        <small>Sem dados</small>
      </div></div>
    </div>
  {/if}

  <!-- Expected days info -->
  <div>
    Esperado: {expectedDays} dias ({year === currentYear ? 'dias decorridos ate hoje' : `ano ${isLeapYear(year) ? 'bissexto' : 'normal'}`})
  </div>

  <!-- Table -->
  <div>
    <div class="table-responsive">
      <table class="data-table">
        <thead>
          <tr>
            <th class="sortable-th" onclick={() => handleSort('tribunal')}>
              Tribunal{sortIcon('tribunal')}
            </th>
            <th class="sortable-th" onclick={() => handleSort('fileCount')}>
              ZIPs{sortIcon('fileCount')}
            </th>
            <th>Esperado</th>
            <th class="sortable-th" onclick={() => handleSort('downloads')}>
              Downloads{sortIcon('downloads')}
            </th>
            <th class="sortable-th" onclick={() => handleSort('percentage')}>
              Cobertura{sortIcon('percentage')}
            </th>
            <th>Progresso</th>
          </tr>
        </thead>
        <tbody>
          {#each sorted as r}
            {@const colors = getCoverageColor(r.percentage)}
            {@const itemId = `djen-${r.tribunal.toLowerCase()}-${year}`}
            <tr>
              <td>
                <a
                  href={`https://archive.org/details/${itemId}`}
                  target="_blank"
                  rel="noopener noreferrer">
                  {r.tribunal}
                </a>
              </td>
              <td>
                {r.fileCount}
              </td>
              <td>
                {r.expectedDays}
              </td>
              <td>
                {r.downloads > 0 ? r.downloads.toLocaleString() : '-'}
              </td>
              <td class={colors.text || undefined}>
                {r.notFound ? 'N/A' : `${r.percentage.toFixed(1)}%`}
                {#if r.error && !r.notFound}
                  <span title={r.error}>!</span>
                {/if}
              </td>
              <td>
                <div
                  class="progress-bar-track"
                  role="progressbar"
                  aria-valuenow={Math.min(100, r.percentage)}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label="{r.tribunal}: {r.percentage.toFixed(1)}% cobertura"
                >
                  <div
                    class={`progress-bar-fill ${colors.bg || ''}`}
                    style="width: {Math.min(100, r.percentage)}%"
                  ></div>
                </div>
              </td>
            </tr>
          {/each}
          {#if results.length === 0 && !loading}
            <tr>
              <td colspan="6">
                Nenhum dado disponivel.
              </td>
            </tr>
          {/if}
        </tbody>
      </table>
    </div>
  </div>
</div>

<style>
  .year-btn {
    display: inline-flex;
    align-items: center;
    padding: 0.375rem 0.75rem;
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-btn);
    background: transparent;
    color: var(--color-base-content);
    cursor: pointer;
    transition: var(--transition-base);
    font-size: var(--font-size-sm);
  }

  .year-btn-active {
    background: var(--color-primary);
    color: var(--color-base-100);
    border-color: var(--color-primary);
  }

  .summary-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin: 1rem 0;
  }

  @media (max-width: 767px) {
    .summary-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  .summary-card {
    background: var(--color-base-100);
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-box);
  }

  .summary-card-body {
    padding: var(--space-sm);
    text-align: center;
  }

  .table-responsive {
    overflow-x: auto;
  }

  .data-table {
    width: 100%;
    border-collapse: collapse;
    font-size: var(--font-size-sm);
  }

  .data-table th,
  .data-table td {
    padding: 0.5rem 0.75rem;
    text-align: left;
  }

  .data-table thead th {
    font-weight: 600;
    border-bottom: 1px solid var(--color-base-300);
  }

  .data-table tbody tr:nth-child(even) {
    background: var(--color-base-200, rgba(0, 0, 0, 0.03));
  }

  .sortable-th {
    cursor: pointer;
    user-select: none;
  }

  .sortable-th:hover {
    color: var(--color-primary);
  }

  .progress-bar-track {
    width: 100%;
    height: 0.5rem;
    background: var(--color-base-200, rgba(0, 0, 0, 0.05));
    border-radius: var(--radius-full);
    overflow: hidden;
  }

  .progress-bar-fill {
    height: 100%;
    border-radius: var(--radius-full);
    transition: width 0.3s ease;
    background: var(--color-primary);
  }
</style>
