<script lang="ts">
  import { onMount } from 'svelte';
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
  let expandedSeq = $state<number | null>(null);
  let searchInputRef = $state<HTMLInputElement | null>(null);

  // The query that was actually submitted by Enter or the explicit Buscar button.
  let submittedQuery = $state<DjenComunicacaoQuery | null>(null);
  let preparedInput = $state('');

  let cooldownUntil = $state<number | null>(null);
  let cooldownRemaining = $state(0);

  const smart = $derived(smartParseInput(preparedInput));
  const effectiveQuery = $derived<DjenComunicacaoQuery>({ ...filters, ...smart.patch });
  const criteriaFilters = $derived({
    siglaTribunal: filters.siglaTribunal,
    numeroOab: filters.numeroOab,
    ufOab: filters.ufOab,
    nomeAdvogado: filters.nomeAdvogado,
    nomeParte: filters.nomeParte,
    numeroProcesso: filters.numeroProcesso,
    dataDisponibilizacaoInicio: filters.dataDisponibilizacaoInicio,
    dataDisponibilizacaoFim: filters.dataDisponibilizacaoFim,
    meio: filters.meio,
    itensPorPagina: filters.itensPorPagina,
  });

  const identityKeys = [
    'siglaTribunal',
    'texto',
    'nomeParte',
    'nomeAdvogado',
    'numeroOab',
    'numeroProcesso',
  ] as const;

  const resultsHeadingId = 'publication-search-results';
  const historicalArchiveHref = `${import.meta.env.BASE_URL.replace(/\/?$/, '/')}dados`;

  // TanStack Query for DJEN search.
  // - `signal` is injected by TanStack; changing `submittedQuery` (key) cancels the previous request.
  // - `staleTime: 60s` so repeated identical searches are served from cache.
  // - No auto-retry on rate-limit or validation errors.
  const searchQuery = createQuery(() => ({
    queryKey: QUERY_KEYS.djenSearch(submittedQuery as Record<string, unknown>),
    queryFn: ({ signal }) => searchDjenComunicacoes(submittedQuery!, { signal }),
    enabled: submittedQuery !== null && queryHasIdentity(submittedQuery) && cooldownRemaining === 0,
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

  const hasPendingInput = $derived(
    rawInput.trim().length >= 3 ||
      hasAnyQueryValue({
        ...filters,
        itensPorPagina: undefined,
        pagina: undefined,
      }),
  );

  const canSubmit = $derived(
    status !== 'loading' && hasPendingInput && cooldownRemaining === 0,
  );

  const preparedSummary = $derived.by(() => buildCriteriaSummary(effectiveQuery));
  const submittedSummary = $derived.by(() =>
    submittedQuery ? buildCriteriaSummary(submittedQuery) : null,
  );
  const hasPreparedCriteria = $derived(preparedSummary.some((item) => item.value !== '—' && item.value !== 'Todos'));
  const isPreparedDifferent = $derived.by(() => {
    if (!submittedQuery) return hasPreparedCriteria;
    return JSON.stringify({ ...effectiveQuery, pagina: undefined }) !==
      JSON.stringify({ ...submittedQuery, pagina: undefined });
  });

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
  let validationDebounceId: ReturnType<typeof setTimeout> | null = null;

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

  $effect(() => {
    return () => stopCooldownTick();
  });

  function queryHasIdentity(query: DjenComunicacaoQuery): boolean {
    return identityKeys.some((k) => {
      const v = query[k];
      return typeof v === 'string' && v.trim().length > 0;
    }) ||
      (typeof query.itensPorPagina === 'number' &&
        query.itensPorPagina > 0 &&
        query.itensPorPagina <= 5);
  }

  function submitSearch({
    page,
    resetPage = false,
    query = effectiveQuery,
  }: { page?: number; resetPage?: boolean; query?: DjenComunicacaoQuery } = {}) {
    if (cooldownRemaining > 0 || !queryHasIdentity(query)) return;
    const nextPage = page ?? (resetPage ? 1 : (query.pagina ?? 1));
    const nextQuery = { ...query, pagina: nextPage };

    if (resetPage && filters.pagina !== nextPage) {
      filters = { ...filters, pagina: nextPage };
    }

    submittedQuery = nextQuery;
    expandedSeq = null;
  }

  function handleSubmit() {
    if (validationDebounceId) {
      clearTimeout(validationDebounceId);
      validationDebounceId = null;
    }
    preparedInput = rawInput;
    submitSearch({
      resetPage: true,
      query: { ...filters, ...smartParseInput(rawInput).patch },
    });
  }

  function handlePageChange(delta: number) {
    const current = filters.pagina ?? 1;
    const next = Math.max(1, current + delta);
    filters = { ...filters, pagina: next };
    submitSearch({ page: next });
  }


  function formatDate(value?: string): string {
    if (!value) return '';
    const [year, month, day] = value.split('-');
    if (year && month && day) return `${day}/${month}/${year}`;
    return value;
  }

  function buildCriteriaSummary(query: DjenComunicacaoQuery) {
    const periodStart = formatDate(query.dataDisponibilizacaoInicio);
    const periodEnd = formatDate(query.dataDisponibilizacaoFim);
    const period = periodStart && periodEnd
      ? `${periodStart} a ${periodEnd}`
      : periodStart
        ? `a partir de ${periodStart}`
        : periodEnd
          ? `até ${periodEnd}`
          : '—';

    const oab = query.numeroOab
      ? [query.ufOab ? `OAB/${query.ufOab}` : 'OAB', query.numeroOab].join(' ')
      : '—';

    const textParts = [query.texto, query.nomeParte, query.nomeAdvogado]
      .filter((value): value is string => typeof value === 'string' && value.trim().length > 0)
      .map((value) => value.trim());

    return [
      { label: 'Tribunal', value: query.siglaTribunal || 'Todos' },
      { label: 'Período', value: period },
      { label: 'OAB', value: oab },
      { label: 'Processo', value: query.numeroProcesso || '—' },
      { label: 'Texto / pessoa', value: textParts.length ? textParts.join(' · ') : '—' },
    ];
  }

  // Debounce only the local preparation layer: validation, hints and smart parsing.
  // Network requests are fired exclusively by Enter, the Buscar button or pagination.
  $effect(() => {
    const _input = rawInput;
    const _criteriaFilters = criteriaFilters;
    void _input;
    void _criteriaFilters;

    if (validationDebounceId) clearTimeout(validationDebounceId);
    validationDebounceId = setTimeout(() => {
      preparedInput = rawInput;
    }, 300);

    return () => {
      if (validationDebounceId) clearTimeout(validationDebounceId);
    };
  });

  // Global keydown for Ctrl+K
  onMount(() => {
    function handleGlobalKeydown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        if (searchInputRef) {
          searchInputRef.focus();
        }
      }
    }
    window.addEventListener('keydown', handleGlobalKeydown);
    return () => {
      window.removeEventListener('keydown', handleGlobalKeydown);
    };
  });

  // Hydrate from URL on mount
  onMount(() => {
    if (typeof window === 'undefined') return;
    const sp = new URLSearchParams(window.location.search);
    if ([...sp.keys()].length === 0) {
       // Focus input automatically if there are no search params
       if (searchInputRef) searchInputRef.focus();
       return;
    }
    const hydrated = searchParamsToQuery(sp);
    filters = {
      ...filters,
      ...hydrated,
      itensPorPagina: hydrated.itensPorPagina ?? 30,
      pagina: hydrated.pagina ?? 1,
    };
    // Reconstruct rawInput so the search field shows what was searched
    if (typeof hydrated.texto === 'string' && hydrated.texto) {
      rawInput = hydrated.texto;
    } else if (hydrated.ufOab && hydrated.numeroOab) {
      rawInput = `OAB ${hydrated.ufOab} ${hydrated.numeroOab}`;
    } else if (hydrated.numeroProcesso) {
      rawInput = hydrated.numeroProcesso;
    }
    preparedInput = rawInput;
    submitSearch({ resetPage: false });
  });
</script>

<section aria-labelledby="publication-search-heading">
  <h2 id="publication-search-heading" class="sr-only">Busca de publicações</h2>

  <SmartSearchInput
    bind:value={rawInput}
    hint={smart.label}
    kind={smart.kind}
    onsubmit={handleSubmit}
    bind:inputRef={searchInputRef}
    disabled={!canSubmit}
    busy={status === 'loading'}
    submitLabel={status === 'loading' ? 'Buscando…' : cooldownRemaining > 0 ? `Aguarde ${cooldownRemaining}s` : 'Buscar'}
  />
  {#if !rawInput}
    <div>
      <small>Experimente:</small>
      <button type="button" class="secondary outline" onclick={() => (rawInput = 'OAB SP 12345')}>OAB SP 12345</button>
      <button type="button" class="secondary outline" onclick={() => (rawInput = 'TJSP')}>TJSP</button>
      <button type="button" class="secondary outline" onclick={() => (rawInput = 'mandado de segurança')}>mandado de segurança</button>
    </div>
  {/if}

  <div>
    <button
      type="button"
      class="secondary outline"
      aria-expanded={showFilters}
      aria-controls="search-filters-panel"
      onclick={() => (showFilters = !showFilters)}
    >
      {showFilters ? 'Ocultar filtros' : 'Filtros avançados'}
    </button>
    <RateLimitBadge limit={rateLimit.limit} remaining={rateLimit.remaining} {usedFallback} />
  </div>



  <section class="criteria-summary" aria-labelledby="criteria-summary-heading">
    <div>
      <strong id="criteria-summary-heading">Critério preparado</strong>
      <p class="meta-text" data-tone="muted">
        {#if hasPreparedCriteria}
          Confira o que será enviado ao DJEN. A API só será chamada ao pressionar Enter ou Buscar.
        {:else}
          Digite uma OAB, processo CNJ, nome ou texto para preparar a busca antes de enviar.
        {/if}
      </p>
    </div>
    <dl>
      {#each preparedSummary as item}
        <div>
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      {/each}
    </dl>
    {#if submittedSummary && !isPreparedDifferent}
      <small data-tone="muted">Este é o mesmo critério da última busca executada.</small>
    {:else if hasPreparedCriteria}
      <small data-tone="warning">Critério preparado, mas ainda não enviado.</small>
    {/if}
  </section>

  {#if showFilters}
    <div id="search-filters-panel">
      <SearchFilters bind:filters />
    </div>
  {/if}

  <div role="status" aria-live="polite" aria-busy={status === 'loading'}>
    {#if status === 'loading'}
      <p aria-busy="true">Buscando publicações…</p>
    {:else if status === 'validation'}
      <div class="alert" data-level="info">
        <strong>Informe um critério de busca.</strong>
        <p>{errorMsg}</p>
      </div>
    {:else if status === 'ratelimited'}
      <div class="alert" data-level="warning">
        <strong>Limite de requisições atingido.</strong>
        <p>Origem: API DJEN online. A cota é controlada por IP pelo DJEN; tente novamente em <b>{cooldownRemaining}s</b>.</p>
        <p>Alternativa: use o arquivo histórico preservado no Internet Archive, que não consome a cota da busca online.</p>
        <a href={historicalArchiveHref} class="secondary outline" role="button">Usar arquivo histórico</a>
      </div>
    {:else if status === 'error'}
      <div class="alert" data-level="error">
        <strong>Não foi possível buscar.</strong>
        <p>{errorMsg}</p>
        <button type="button" onclick={handleSubmit}>Tentar novamente</button>
      </div>
    {:else if status === 'empty'}
      <p class="meta-text" data-tone="muted">
        <strong>Nenhum resultado.</strong>
        Ajuste os filtros ou amplie o período.
      </p>
    {:else if status === 'success'}
      {@const perPage = filters.itensPorPagina ?? 30}
      {@const currentPage = filters.pagina ?? 1}
      {@const totalPages = Math.max(1, Math.ceil(totalCount / perPage))}
      <header id={resultsHeadingId}>
        <small class="meta-text">{totalCount.toLocaleString('pt-BR')} resultado(s)</small>
        <div>
          <button
            type="button"
            class="secondary outline"
            disabled={currentPage <= 1}
            onclick={() => handlePageChange(-1)}
          >‹ Anterior</button>
          <span>Página {currentPage} de {totalPages.toLocaleString('pt-BR')}</span>
          <button
            type="button"
            class="secondary outline"
            disabled={currentPage >= totalPages || results.length < perPage}
            onclick={() => handlePageChange(1)}
          >Próxima ›</button>
        </div>
      </header>
      <ul aria-label="Resultados da busca">
        {#each results as pub, i (pub.hash ?? pub.numeroComunicacao ?? i)}
          <li>
            <PublicationCard
              {pub}
              seq={i + 1}
              dateStr={pub.data_disponibilizacao ?? ''}
              compact={expandedSeq !== i + 1}
              totalSeq={results.length}
              source="djen"
              {usedFallback}
              onExpand={() => (expandedSeq = i + 1)}
              onCollapse={() => (expandedSeq = null)}
              onNavigate={(newSeq) => (expandedSeq = newSeq)}
            />
          </li>
        {/each}
      </ul>
    {:else}
      <p class="meta-text" data-tone="muted">Comece digitando um número de OAB, um processo CNJ ou um termo livre. A busca só será enviada ao DJEN quando você pressionar Enter ou Buscar.</p>
    {/if}
  </div>
</section>


<style>
  .criteria-summary {
    margin-block: 1rem;
    padding: 1rem;
    border: 1px solid var(--border, var(--concreto-90, #d8d8d8));
    border-radius: var(--radius, 0.75rem);
    background: var(--papel-20, rgba(0, 0, 0, 0.02));
  }

  .criteria-summary dl {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(9rem, 1fr));
    gap: 0.75rem;
    margin: 0.75rem 0;
  }

  .criteria-summary dt {
    font-size: 0.75rem;
    color: var(--fg-muted, var(--color-content-tertiary));
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }

  .criteria-summary dd {
    margin: 0;
    font-weight: 600;
    overflow-wrap: anywhere;
  }
</style>
