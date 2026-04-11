<script lang="ts">
  import { onMount, untrack } from 'svelte';
  import { createQuery, setQueryClientContext } from '@tanstack/svelte-query';
  import {
    searchDjenComunicacoes,
    DjenValidationError,
    DjenRateLimitError,
    type DjenComunicacaoQuery,
    type DjenPublication,
    type DjenRateLimit,
  } from '../lib/djen';
  import {
    smartParseInput,
    pushQueryToUrl,
    searchParamsToQuery,
    hasAnyQueryValue,
  } from '../lib/searchQueryString';
  import PublicationCard from './PublicationCard.svelte';
  import SmartSearchInput from './SmartSearchInput.svelte';
  import SearchFilters from './SearchFilters.svelte';
  import RateLimitBadge from './RateLimitBadge.svelte';
  import { QUERY_KEYS } from '../lib/queryKeys';
  import { getQueryClient } from '../lib/queryClient';

  // Initialize context for this island (must run during component init, before createQuery)
  setQueryClientContext(getQueryClient());

  type Status =
    | 'idle'
    | 'loading'
    | 'success'
    | 'empty'
    | 'error'
    | 'ratelimited'
    | 'validation';

  let rawInput = $state('');
  let filters = $state<DjenComunicacaoQuery>({ itensPorPagina: 30, pagina: 1 });
  let showFilters = $state(false);

  // The query that was actually submitted (debounced or immediate on submit)
  let submittedQuery = $state<DjenComunicacaoQuery | null>(null);

  let cooldownUntil = $state<number | null>(null);
  let cooldownRemaining = $state(0);

  const smart = $derived(smartParseInput(rawInput));
  const effectiveQuery = $derived<DjenComunicacaoQuery>({ ...filters, ...smart.patch });

  const identityKeys = [
    'siglaTribunal',
    'texto',
    'nomeParte',
    'nomeAdvogado',
    'numeroOab',
    'numeroProcesso',
  ] as const;

  const hasIdentity = $derived(
    identityKeys.some((k) => {
      const v = effectiveQuery[k];
      return typeof v === 'string' && v.trim().length > 0;
    }) ||
      (typeof effectiveQuery.itensPorPagina === 'number' &&
        effectiveQuery.itensPorPagina > 0 &&
        effectiveQuery.itensPorPagina <= 5),
  );

  const resultsHeadingId = 'publication-search-results';

  // TanStack Query for DJEN search.
  // - `signal` is injected by TanStack; changing `submittedQuery` (key) cancels the previous request.
  // - `staleTime: 60s` so repeated identical searches are served from cache.
  // - No auto-retry on rate-limit or validation errors.
  const searchQuery = createQuery(() => ({
    queryKey: QUERY_KEYS.djenSearch(submittedQuery as Record<string, unknown>),
    queryFn: ({ signal }) => searchDjenComunicacoes(submittedQuery!, { signal }),
    enabled: submittedQuery !== null && hasIdentity && cooldownRemaining === 0,
    staleTime: 60_000,
    retry: (failureCount, error) => {
      if (error instanceof DjenRateLimitError) return false;
      if (error instanceof DjenValidationError) return false;
      return failureCount < 2;
    },
  }));

  // Derive display state from query result
  const results = $derived<DjenPublication[]>(searchQuery.data?.items ?? []);
  const totalCount = $derived(searchQuery.data?.count ?? 0);
  const rateLimit = $derived<DjenRateLimit>(
    searchQuery.data?.rateLimit ?? { limit: null, remaining: null, resetAt: null }
  );
  const usedFallback = $derived(searchQuery.data?.usedFallback ?? false);

  const status = $derived.by((): Status => {
    if (searchQuery.isFetching) return 'loading';
    const err = searchQuery.error;
    if (err) {
      if (err instanceof DjenRateLimitError) return 'ratelimited';
      if (err instanceof DjenValidationError) return 'validation';
      return 'error';
    }
    if (searchQuery.isSuccess) {
      return results.length === 0 ? 'empty' : 'success';
    }
    return 'idle';
  });

  const errorMsg = $derived.by((): string | null => {
    const err = searchQuery.error;
    if (!err) return null;
    if (err instanceof DjenValidationError) return err.issues.join(' · ');
    if (err instanceof DjenRateLimitError) return null;
    return (err as Error).message || 'Erro desconhecido';
  });

  const canSubmit = $derived(
    status !== 'loading' && hasIdentity && cooldownRemaining === 0,
  );

  // Watch for rate-limit errors and start the cooldown timer
  $effect(() => {
    const err = searchQuery.error;
    if (err instanceof DjenRateLimitError && cooldownUntil === null) {
      cooldownUntil = Date.now() + err.retryAfterSec * 1000;
      cooldownRemaining = err.retryAfterSec;
      startCooldownTick();
    }
  });

  // Sync URL when a successful search completes
  $effect(() => {
    if (searchQuery.isSuccess && submittedQuery) {
      pushQueryToUrl(submittedQuery);
    }
  });

  let cooldownInterval: ReturnType<typeof setInterval> | null = null;
  let debounceId: ReturnType<typeof setTimeout> | null = null;

  function startCooldownTick() {
    stopCooldownTick();
    cooldownInterval = setInterval(() => {
      if (cooldownUntil === null) {
        stopCooldownTick();
        return;
      }
      const remaining = Math.max(0, Math.ceil((cooldownUntil - Date.now()) / 1000));
      cooldownRemaining = remaining;
      if (remaining <= 0) {
        cooldownUntil = null;
        stopCooldownTick();
      }
    }, 1000);
  }

  function stopCooldownTick() {
    if (cooldownInterval) {
      clearInterval(cooldownInterval);
      cooldownInterval = null;
    }
  }

  function submitSearch() {
    if (cooldownRemaining > 0 || !hasIdentity) return;
    submittedQuery = { ...effectiveQuery };
  }

  function handleSubmit() {
    if (debounceId) {
      clearTimeout(debounceId);
      debounceId = null;
    }
    submitSearch();
  }

  function handlePageChange(delta: number) {
    const current = filters.pagina ?? 1;
    const next = Math.max(1, current + delta);
    filters = { ...filters, pagina: next };
    submittedQuery = { ...effectiveQuery, pagina: next };
  }

  // Debounced reactive trigger
  $effect(() => {
    const _input = rawInput;
    const _filters = filters;
    void _input;
    void _filters;

    if (debounceId) clearTimeout(debounceId);
    debounceId = setTimeout(() => {
      untrack(() => {
        const trimmed = rawInput.trim();
        const hasFilterValues = hasAnyQueryValue({
          ...filters,
          itensPorPagina: undefined,
          pagina: undefined,
        });
        if (trimmed.length >= 3 || hasFilterValues) {
          submitSearch();
        }
      });
    }, 400);

    return () => {
      if (debounceId) clearTimeout(debounceId);
    };
  });

  // Hydrate from URL on mount
  onMount(() => {
    if (typeof window === 'undefined') return;
    const sp = new URLSearchParams(window.location.search);
    if ([...sp.keys()].length === 0) return;
    const hydrated = searchParamsToQuery(sp);
    filters = {
      ...filters,
      ...hydrated,
      itensPorPagina: hydrated.itensPorPagina ?? 30,
      pagina: hydrated.pagina ?? 1,
    };
    if (typeof hydrated.texto === 'string' && hydrated.texto) {
      rawInput = hydrated.texto;
    }
    // debounced effect will fire the search
  });
</script>

<section class="search-root" aria-labelledby="publication-search-heading">
  <h2 id="publication-search-heading" class="visually-hidden">Busca de publicações</h2>

  <SmartSearchInput bind:value={rawInput} hint={smart.label} onsubmit={handleSubmit} />

  <div class="search-toolbar">
    <button
      type="button"
      class="toggle-btn"
      aria-expanded={showFilters}
      aria-controls="search-filters-panel"
      onclick={() => (showFilters = !showFilters)}
    >
      {showFilters ? 'Ocultar filtros' : 'Filtros avançados'}
    </button>
    <button type="button" class="submit-btn" disabled={!canSubmit} onclick={handleSubmit}>
      {status === 'loading' ? 'Buscando…' : cooldownRemaining > 0 ? `Aguarde ${cooldownRemaining}s` : 'Buscar'}
    </button>
    <div class="toolbar-spacer"></div>
    <RateLimitBadge limit={rateLimit.limit} remaining={rateLimit.remaining} {usedFallback} />
  </div>

  {#if showFilters}
    <div id="search-filters-panel">
      <SearchFilters bind:filters />
    </div>
  {/if}

  <div class="status-region" aria-live="polite" aria-busy={status === 'loading'}>
    {#if status === 'loading'}
      <ul class="skeleton-list" aria-hidden="true">
        {#each Array.from({ length: 5 }) as _, i (i)}
          <li class="skeleton-card">
            <div class="skeleton-line w-60"></div>
            <div class="skeleton-line w-80"></div>
            <div class="skeleton-line w-40"></div>
          </li>
        {/each}
      </ul>
    {:else if status === 'validation'}
      <div class="banner info">
        <strong>Informe um critério de busca.</strong>
        <p>{errorMsg}</p>
      </div>
    {:else if status === 'ratelimited'}
      <div class="banner warning">
        <strong>Limite de requisições atingido.</strong>
        <p>A API do DJEN controla a taxa por IP. Tente novamente em <b>{cooldownRemaining}s</b>.</p>
      </div>
    {:else if status === 'error'}
      <div class="banner danger">
        <strong>Não foi possível buscar.</strong>
        <p>{errorMsg}</p>
        <button type="button" onclick={handleSubmit}>Tentar novamente</button>
      </div>
    {:else if status === 'empty'}
      <div class="banner muted">
        <strong>Nenhum resultado.</strong>
        <p>Ajuste os filtros ou amplie o período.</p>
      </div>
    {:else if status === 'success'}
      <div class="results-header" id={resultsHeadingId}>
        <span class="result-count">{totalCount.toLocaleString('pt-BR')} resultado(s)</span>
        <div class="pagination">
          <button
            type="button"
            disabled={(filters.pagina ?? 1) <= 1}
            onclick={() => handlePageChange(-1)}
          >‹ Anterior</button>
          <span>Página {filters.pagina ?? 1}</span>
          <button
            type="button"
            disabled={results.length < (filters.itensPorPagina ?? 30)}
            onclick={() => handlePageChange(1)}
          >Próxima ›</button>
        </div>
      </div>
      <ul class="result-list" aria-label="Resultados da busca">
        {#each results as pub, i (pub.hash ?? pub.numeroComunicacao ?? i)}
          <li>
            <PublicationCard
              {pub}
              seq={i + 1}
              dateStr={pub.data_disponibilizacao ?? ''}
              compact
              source="djen"
              {usedFallback}
            />
          </li>
        {/each}
      </ul>
    {:else}
      <div class="banner muted idle">
        <p>Comece digitando um número de OAB, um processo CNJ ou um termo livre para buscar ao vivo no DJEN.</p>
      </div>
    {/if}
  </div>
</section>

<style>
  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  .search-root {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
  }

  .search-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.6rem;
  }

  .toolbar-spacer {
    flex: 1;
  }

  .toggle-btn,
  .submit-btn {
    padding: 0.55rem 1rem;
    border-radius: var(--radius-sm, 0.5rem);
    border: 1px solid var(--color-base-300);
    background: var(--color-base-100);
    color: inherit;
    font-size: var(--font-size-sm, 0.875rem);
    cursor: pointer;
    font-weight: 600;
  }

  .toggle-btn:hover {
    border-color: var(--color-primary, #3b82f6);
    color: var(--color-primary, #3b82f6);
  }

  .submit-btn {
    background: var(--color-primary, #3b82f6);
    color: white;
    border-color: transparent;
  }

  .submit-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .submit-btn:not(:disabled):hover {
    filter: brightness(0.95);
  }

  .status-region {
    min-height: 3rem;
  }

  .banner {
    padding: 1rem 1.25rem;
    border-radius: var(--radius-box, 0.75rem);
    border: 1px solid var(--color-base-300);
    background: var(--color-base-100);
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .banner strong {
    font-size: var(--font-size-base, 1rem);
  }

  .banner p {
    margin: 0;
    opacity: 0.8;
    font-size: var(--font-size-sm, 0.875rem);
  }

  .banner button {
    align-self: flex-start;
    margin-top: 0.5rem;
    padding: 0.4rem 0.85rem;
    border: 1px solid currentColor;
    border-radius: var(--radius-sm, 0.375rem);
    background: transparent;
    color: inherit;
    cursor: pointer;
    font-size: var(--font-size-xs, 0.75rem);
  }

  .banner.info {
    border-color: #3b82f6;
    color: #1e40af;
  }

  .banner.warning {
    border-color: #d97706;
    color: #92400e;
  }

  .banner.danger {
    border-color: #dc2626;
    color: #991b1b;
  }

  .banner.muted {
    opacity: 0.8;
  }

  .banner.idle {
    border-style: dashed;
  }

  .skeleton-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .skeleton-card {
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-box, 0.75rem);
    background: var(--color-base-100);
    padding: 1rem 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .skeleton-line {
    height: 0.75rem;
    border-radius: 0.25rem;
    background: linear-gradient(
      90deg,
      var(--color-base-200, #e5e7eb) 0%,
      var(--color-base-300, #d1d5db) 50%,
      var(--color-base-200, #e5e7eb) 100%
    );
    background-size: 200% 100%;
    animation: shimmer 1.4s infinite;
  }

  .w-40 {
    width: 40%;
  }
  .w-60 {
    width: 60%;
  }
  .w-80 {
    width: 80%;
  }

  @keyframes shimmer {
    0% {
      background-position: 200% 0;
    }
    100% {
      background-position: -200% 0;
    }
  }

  .results-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.75rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--color-base-200);
    flex-wrap: wrap;
  }

  .result-count {
    font-weight: 600;
    font-size: var(--font-size-sm, 0.875rem);
    opacity: 0.8;
  }

  .pagination {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: var(--font-size-sm, 0.875rem);
  }

  .pagination button {
    padding: 0.35rem 0.75rem;
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-sm, 0.375rem);
    background: var(--color-base-100);
    color: inherit;
    cursor: pointer;
    font-size: var(--font-size-xs, 0.75rem);
  }

  .pagination button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .result-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
  }
</style>
