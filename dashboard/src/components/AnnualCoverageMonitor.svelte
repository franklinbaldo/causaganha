<script lang="ts">
import { onMount } from 'svelte';
import { fetchAllTribunalMetadata, clearCache, getExpectedDays, type TribunalMetadata } from '../lib/iaMetadataFetcher';
import { getCoverageColor } from '../lib/colorUtils';
import { isLeapYear } from '../lib/dateUtils';

const currentYear = new Date().getFullYear();
const YEARS = [currentYear - 2, currentYear - 1, currentYear];

let year = $state(currentYear);
let results = $state<TribunalMetadata[]>([]);
let loading = $state(false);
let sortBy = $state('percentage');
let sortDir = $state('desc');

function fetchData(forceRefresh: boolean = false) {
  loading = true;

  if (forceRefresh) clearCache(year);

  fetchAllTribunalMetadata(year, (_done, _total, partial) => {
    results = [...partial];
  }, { useCache: !forceRefresh }).then((final) => {
    results = final;
    loading = false;
  }).catch(() => {
    loading = false;
  });
}

$effect(() => {
  // Re-fetch whenever year changes
  fetchData();
});

function handleSort(field: string) {
  if (sortBy === field) {
    sortDir = sortDir === 'asc' ? 'desc' : 'asc';
  } else {
    sortBy = field;
    sortDir = field === 'tribunal' ? 'asc' : 'desc';
  }
}

const sorted = $derived.by(() => {
  return [...results].sort((a, b) => {
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
const complete = $derived(results.filter(r => r.percentage >= 90).length);
const partial = $derived(results.filter(r => r.percentage >= 50 && r.percentage < 90).length);
const low = $derived(results.filter(r => r.percentage > 0 && r.percentage < 50).length);
const missing = $derived(results.filter(r => r.percentage === 0).length);

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
            class={year === y ? "btn" : "btn btn-secondary"}>
            {y}
          </button>
        {/each}
      </div>
      <button
        onclick={() => fetchData(true)}
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
    <div class="grid">
      <div class="card bg-base-100 shadow-sm border border-base-300"><div class="card-body">
        <div>{complete}</div>
        <small>&gt;90%</small>
      </div></div>
      <div class="card bg-base-100 shadow-sm border border-base-300"><div class="card-body">
        <div>{partial}</div>
        <small>50-89%</small>
      </div></div>
      <div class="card bg-base-100 shadow-sm border border-base-300"><div class="card-body">
        <div>{low}</div>
        <small>&lt;50%</small>
      </div></div>
      <div class="card bg-base-100 shadow-sm border border-base-300"><div class="card-body">
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
      <table class="table table-zebra table-sm">
        <thead>
          <tr>
            <th onclick={() => handleSort('tribunal')}>
              Tribunal{sortIcon('tribunal')}
            </th>
            <th onclick={() => handleSort('fileCount')}>
              ZIPs{sortIcon('fileCount')}
            </th>
            <th>Esperado</th>
            <th onclick={() => handleSort('downloads')}>
              Downloads{sortIcon('downloads')}
            </th>
            <th onclick={() => handleSort('percentage')}>
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
                <div>
                  <div
                    class={colors.bg || undefined}
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
