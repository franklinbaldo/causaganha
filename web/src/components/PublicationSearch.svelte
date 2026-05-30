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

  type PublicationHashTarget =
    | { kind: 'hash' | 'numeroComunicacao' | 'id'; value: string }
    | { kind: 'seq'; value: number };

  let rawInput = $state('');
  let filters = $state<DjenComunicacaoQuery>({ itensPorPagina: 30, pagina: 1 });
  let showFilters = $state(false);
  let expandedSeq = $state<number | null>(null);
  let pendingPublicationTarget = $state<PublicationHashTarget | null>(null);
  let searchInputRef = $state<HTMLInputElement | null>(null);

  // The query that was actually submitted (debounced or immediate on submit)
  let submittedQuery = $state<DjenComunicacaoQuery | null>(null);

  let cooldownUntil = $state<number | null>(null);
  let cooldownRemaining = $state(0);

  type ActiveFilterChip = {
    key: string;
    label: string;
    value: string;
  };

  const DEFAULT_ITEMS_PER_PAGE = 30;

  function formatDateLabel(value: string): string {
    const [year, month, day] = value.split('-');
    if (!year || !month || !day) return value;
    return `${day}/${month}/${year}`;
  }

  function periodLabel(query: DjenComunicacaoQuery): string | null {
    const start = query.dataDisponibilizacaoInicio;
    const end = query.dataDisponibilizacaoFim;
    if (start && end) return `${formatDateLabel(start)} a ${formatDateLabel(end)}`;
    if (start) return `A partir de ${formatDateLabel(start)}`;
    if (end) return `Até ${formatDateLabel(end)}`;
    return null;
  }

  const activeFilterChips = $derived.by((): ActiveFilterChip[] => {
    const query = effectiveQuery;
    const chips: ActiveFilterChip[] = [];
    const period = periodLabel(query);

    if (query.siglaTribunal) {
      chips.push({ key: 'siglaTribunal', label: 'Tribunal', value: query.siglaTribunal });
    }
    if (period) {
      chips.push({ key: 'periodo', label: 'Período', value: period });
    }
    if (query.numeroOab) {
      chips.push({ key: 'numeroOab', label: 'OAB', value: query.numeroOab });
    }
    if (query.ufOab) {
      chips.push({ key: 'ufOab', label: 'UF', value: query.ufOab });
    }
    if (query.nomeAdvogado) {
      chips.push({ key: 'nomeAdvogado', label: 'Advogado', value: query.nomeAdvogado });
    }
    if (query.nomeParte) {
      chips.push({ key: 'nomeParte', label: 'Parte', value: query.nomeParte });
    }
    if (query.meio) {
      chips.push({ key: 'meio', label: 'Meio', value: query.meio === 'D' ? 'Diário' : 'Edital' });
    }
    if (query.itensPorPagina && query.itensPorPagina !== DEFAULT_ITEMS_PER_PAGE) {
      chips.push({
        key: 'itensPorPagina',
        label: 'Itens por página',
        value: String(query.itensPorPagina),
      });
    }

    return chips;
  });

  const smart = $derived(smartParseInput(rawInput));
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

  function parsePublicationHash(hash: string): PublicationHashTarget | null {
    const value = hash.replace(/^#/, '');
    if (!value) return null;

    const pubMatch = value.match(/(?:^|\/)pub\/(hash|numeroComunicacao|id)\/([^/]+)/);
    if (pubMatch) {
      return {
        kind: pubMatch[1] as 'hash' | 'numeroComunicacao' | 'id',
        value: decodeURIComponent(pubMatch[2]),
      };
    }

    const seqMatch = value.match(/(?:^|\/)seq\/(\d+)$/);
    if (seqMatch) {
      return { kind: 'seq', value: Number(seqMatch[1]) };
    }

    return null;
  }

  function publicationMatchesTarget(pub: DjenPublication, target: PublicationHashTarget): boolean {
    if (target.kind === 'seq') return false;
    if (target.kind === 'hash') return pub.hash === target.value;
    if (target.kind === 'numeroComunicacao') {
      return pub.numeroComunicacao != null && String(pub.numeroComunicacao) === target.value;
    }
    return pub.id != null && String(pub.id) === target.value;
  }

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

  $effect(() => {
    const target = pendingPublicationTarget;
    const _results = results;
    void _results;

    if (!target || !searchQuery.isSuccess) return;

    if (target.kind === 'seq') {
      if (target.value >= 1 && target.value <= results.length) {
        expandedSeq = target.value;
        pendingPublicationTarget = null;
      }
      return;
    }

    const index = results.findIndex((pub) => publicationMatchesTarget(pub, target));
    if (index >= 0) {
      expandedSeq = index + 1;
      pendingPublicationTarget = null;
    }
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

  $effect(() => {
    return () => stopCooldownTick();
  });

  function submitSearch({
    page,
    resetPage = false,
  }: { page?: number; resetPage?: boolean } = {}) {
    if (cooldownRemaining > 0 || !hasIdentity) return;
    const nextPage = page ?? (resetPage ? 1 : (effectiveQuery.pagina ?? 1));
    const nextQuery = { ...effectiveQuery, pagina: nextPage };

    if (resetPage && filters.pagina !== nextPage) {
      filters = { ...filters, pagina: nextPage };
    }

    submittedQuery = nextQuery;
    expandedSeq = null;
  }

  function handleSubmit() {
    if (debounceId) {
      clearTimeout(debounceId);
      debounceId = null;
    }
    submitSearch({ resetPage: true });
  }

  function handlePageChange(delta: number) {
    const current = filters.pagina ?? 1;
    const next = Math.max(1, current + delta);
    filters = { ...filters, pagina: next };
    submitSearch({ page: next });
  }


  function removeActiveFilter(key: ActiveFilterChip['key']) {
    const patch: Partial<DjenComunicacaoQuery> = { pagina: 1 };

    if (key === 'siglaTribunal') patch.siglaTribunal = undefined;
    if (key === 'periodo') {
      patch.dataDisponibilizacaoInicio = undefined;
      patch.dataDisponibilizacaoFim = undefined;
    }
    if (key === 'numeroOab') {
      patch.numeroOab = undefined;
      if (smart.patch.numeroOab) rawInput = '';
    }
    if (key === 'ufOab') {
      patch.ufOab = undefined;
      if (smart.patch.ufOab) rawInput = '';
    }
    if (key === 'nomeAdvogado') patch.nomeAdvogado = undefined;
    if (key === 'nomeParte') patch.nomeParte = undefined;
    if (key === 'meio') patch.meio = undefined;
    if (key === 'itensPorPagina') patch.itensPorPagina = DEFAULT_ITEMS_PER_PAGE;

    filters = { ...filters, ...patch };
  }

  // Debounced reactive trigger for criteria changes. Pagination changes are handled separately.
  $effect(() => {
    const _input = rawInput;
    const _criteriaFilters = criteriaFilters;
    void _input;
    void _criteriaFilters;

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
          submitSearch({ resetPage: true });
        }
      });
    }, 400);

    return () => {
      if (debounceId) clearTimeout(debounceId);
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
    pendingPublicationTarget = parsePublicationHash(window.location.hash);
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
    // debounced effect will fire the search
  });
</script>

<section class="publication-search" aria-labelledby="publication-search-heading">
  <h2 id="publication-search-heading" class="sr-only">Busca de publicações</h2>

  <SmartSearchInput bind:value={rawInput} hint={smart.label} kind={smart.kind} onsubmit={handleSubmit} bind:inputRef={searchInputRef} />

  <section aria-label="Filtros ativos">
    <strong>Filtros ativos</strong>
    {#if activeFilterChips.length > 0}
      <ul aria-label="Lista de filtros ativos">
        {#each activeFilterChips as chip (chip.key)}
          <li>
            <button
              type="button"
              class="secondary outline"
              aria-label={`Remover filtro ${chip.label}: ${chip.value}`}
              title={`Remover filtro ${chip.label}`}
              onclick={() => removeActiveFilter(chip.key)}
            >
              <span>{chip.label}: {chip.value}</span>
              <span aria-hidden="true">×</span>
            </button>
          </li>
        {/each}
      </ul>
    {:else}
      <small class="meta-text" data-tone="muted">Nenhum filtro ativo.</small>
    {/if}
  </section>

  {#if !rawInput}
    <div class="publication-search__examples">
      <small>Experimente:</small>
      <button type="button" class="secondary outline" onclick={() => (rawInput = 'OAB SP 12345')}>OAB SP 12345</button>
      <button type="button" class="secondary outline" onclick={() => (rawInput = 'TJSP')}>TJSP</button>
      <button type="button" class="secondary outline" onclick={() => (rawInput = 'mandado de segurança')}>mandado de segurança</button>
    </div>
  {/if}

  <div class="publication-search__actions">
    <button
      type="button"
      class="secondary outline"
      aria-expanded={showFilters}
      aria-controls="search-filters-panel"
      onclick={() => (showFilters = !showFilters)}
    >
      {showFilters ? 'Ocultar filtros' : 'Filtros avançados'}
    </button>
    <button
      type="button"
      disabled={!canSubmit}
      aria-busy={status === 'loading'}
      onclick={handleSubmit}
    >
      {#if status === 'loading'}
        <span aria-busy="true" aria-hidden="true"></span>
        Buscando…
      {:else if cooldownRemaining > 0}
        Aguarde {cooldownRemaining}s
      {:else}
        Buscar
      {/if}
    </button>
    <RateLimitBadge limit={rateLimit.limit} remaining={rateLimit.remaining} {usedFallback} />
  </div>

  {#if showFilters}
    <div id="search-filters-panel" class="publication-search__filter-panel">
      <SearchFilters bind:filters />
    </div>
  {/if}

  <div class="publication-search__status" role="status" aria-live="polite" aria-busy={status === 'loading'}>
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
        <p>A API do DJEN controla a taxa por IP. Tente novamente em <b>{cooldownRemaining}s</b>.</p>
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
      <header id={resultsHeadingId} class="publication-search__results-header">
        <small class="meta-text">{totalCount.toLocaleString('pt-BR')} resultado(s)</small>
        <div class="publication-search__pagination">
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
      <ul class="publication-search__results-list" aria-label="Resultados da busca" aria-busy={searchQuery.isFetching}>
        {#each results as pub, i (pub.hash ?? pub.numeroComunicacao ?? i)}
          <li class="publication-search__result-item">
            <PublicationCard
              {pub}
              seq={i + 1}
              dateStr={pub.data_disponibilizacao ?? ''}
              compact={expandedSeq !== i + 1}
              totalSeq={results.length}
              source={usedFallback ? 'ia' : 'djen'}
              {usedFallback}
              onExpand={() => (expandedSeq = i + 1)}
              onCollapse={() => (expandedSeq = null)}
              onNavigate={(newSeq) => (expandedSeq = newSeq)}
            />
          </li>
        {/each}
      </ul>
    {:else}
      <p class="meta-text" data-tone="muted">Comece digitando um número de OAB, um processo CNJ ou um termo livre para buscar ao vivo no DJEN.</p>
    {/if}
  </div>
</section>
