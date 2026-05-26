<script lang="ts">
import { createQuery, useQueryClient, setQueryClientContext } from '@tanstack/svelte-query';
import { fetchAllTribunalMetadata, getExpectedDays, type TribunalMetadata } from '../lib/iaMetadataFetcher';
import { isLeapYear } from '../lib/dateUtils';
import { QUERY_KEYS } from '../lib/queryKeys';
import { getQueryClient } from '../lib/queryClient';
import YearSummaryCards from './YearSummaryCards.svelte';
import CoverageTable from './CoverageTable.svelte';

// Initialize context for this island (must run during component init, before createQuery)
setQueryClientContext(getQueryClient());

const queryClient = useQueryClient();
const currentYear = new Date().getFullYear();
const YEARS = [currentYear - 2, currentYear - 1, currentYear];

let year = $state(currentYear);

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

const results = $derived(coverageQuery.data ?? []);
const loading = $derived(coverageQuery.isLoading || coverageQuery.isFetching);

const expectedDays = $derived(getExpectedDays(year));
const complete = $derived(results.filter((r: TribunalMetadata) => r.percentage >= 90).length);
const partial = $derived(results.filter((r: TribunalMetadata) => r.percentage >= 50 && r.percentage < 90).length);
const low = $derived(results.filter((r: TribunalMetadata) => r.percentage > 0 && r.percentage < 50).length);
const missing = $derived(results.filter((r: TribunalMetadata) => r.percentage === 0).length);
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
            type="button"
            onclick={() => { year = y; }}
            aria-pressed={year === y}
            class={year === y ? "" : "outline"}>
            {y}
          </button>
        {/each}
      </div>
      <button
        type="button"
        onclick={() => handleForceRefresh()}
        disabled={loading}
        aria-busy={loading}
        title="Atualizar dados">
        {loading ? 'Atualizando…' : 'Atualizar'}
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
    <YearSummaryCards {complete} {partial} {low} {missing} />
  {/if}

  <!-- Expected days info -->
  <div>
    Esperado: {expectedDays} dias ({year === currentYear ? 'dias decorridos até hoje' : `ano ${isLeapYear(year) ? 'bissexto' : 'normal'}`})
  </div>

  <!-- Table -->
  <CoverageTable {results} {expectedDays} {year} {loading} />
</div>
