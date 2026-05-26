<script lang="ts">
import { type TribunalMetadata } from '../lib/iaMetadataFetcher';
import { getCoverageColor } from '../lib/colorUtils';

interface Props {
  results: TribunalMetadata[];
  expectedDays: number;
  year: number;
  loading: boolean;
}

const { results, expectedDays, year, loading }: Props = $props();

let sortBy = $state('percentage');
let sortDir = $state('desc');

function handleSort(field: string) {
  if (sortBy === field) {
    sortDir = sortDir === 'asc' ? 'desc' : 'asc';
  } else {
    sortBy = field;
    sortDir = field === 'tribunal' ? 'asc' : 'desc';
  }
}

function sortIcon(field: string): string {
  if (sortBy !== field) return '';
  return sortDir === 'asc' ? ' ↑' : ' ↓';
}

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
</script>

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
            {r.downloads > 0 ? r.downloads.toLocaleString('pt-BR') : '-'}
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
            Nenhum dado disponível.
          </td>
        </tr>
      {/if}
    </tbody>
  </table>
</div>
