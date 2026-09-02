<script lang="ts">
import { createQuery, useQueryClient, setQueryClientContext } from '@tanstack/svelte-query';
import { fetchAllTribunalMetadata, getExpectedDays, type TribunalMetadata } from '../lib/iaMetadataFetcher';
import { isLeapYear } from '../lib/dateUtils';
import { QUERY_KEYS } from '../lib/queryKeys';
import { getQueryClient } from '../lib/queryClient';
import YearSummaryCards from './YearSummaryCards.svelte';
import CoverageTable from './CoverageTable.svelte';
import AlertBanner from './AlertBanner.svelte';

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

// `fetchAllTribunalMetadata` never throws: a total upstream failure (the IA
// Advanced Search call itself) still resolves one row per tribunal, all
// `notFound: true` with the same `error` message. Rendering that as a normal
// 0%/N/A table would conflate "fonte indisponível" with a confirmed absence
// of archived files (issue #907) — so it gets a distinct state instead.
const sourceUnavailable = $derived(
  !loading && results.length > 0 && results.every((r: TribunalMetadata) => r.error != null),
);

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

  {#if sourceUnavailable}
    <AlertBanner
      level="error"
      title="Não foi possível verificar a cobertura."
      message="A consulta ao Internet Archive falhou; isso não confirma ausência de arquivos nos tribunais consultados." />
    <button type="button" onclick={() => handleForceRefresh()}>Tentar novamente</button>
  {:else}
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
  {/if}
</div>
