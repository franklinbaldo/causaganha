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
  import { formatCnj } from '../lib/processoCnj';
  import {
    SAVED_CONSULTATIONS_STORAGE_KEY,
    parseSavedConsultations,
    removeSavedConsultation,
    saveSearchConsultation,
    searchConsultationId,
    serializeSavedConsultations,
  } from '../lib/savedConsultations';
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

  // The query that was actually submitted by Enter or the explicit Buscar button.
  let submittedQuery = $state<DjenComunicacaoQuery | null>(null);
  let preparedInput = $state('');

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

  const smart = $derived(smartParseInput(preparedInput));
  // Este formulário só consulta o DJEN. Quando o input é um CNJ válido, o
  // dossiê reconciliado em /processo tem mais fontes (DJEN + JURIS + STJ +
  // DataJud) do que esta busca sozinha — por isso o link em vez de fundir
  // as duas UIs.
  const BASE_URL = import.meta.env.BASE_URL;
  const processoHref = $derived.by(() => {
    if (smart.kind !== 'processo' || !smart.patch.numeroProcesso) return null;
    const base = BASE_URL.endsWith('/') ? BASE_URL : `${BASE_URL}/`;
    return `${base}processo?cnj=${encodeURIComponent(formatCnj(smart.patch.numeroProcesso))}`;
  });
  const tribunalCoverageHref = $derived.by(() => {
    const tribunal = submittedQuery?.siglaTribunal?.trim();
    if (!tribunal) return null;
    const base = BASE_URL.endsWith('/') ? BASE_URL : `${BASE_URL}/`;
    return `${base}publicacoes/${encodeURIComponent(tribunal.toLowerCase())}`;
  });
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
  const historicalArchiveHref = 'https://archive.org/details/causaganha-dashboard';

  let searchLinkCopied = $state(false);
  let searchLinkTimeout: ReturnType<typeof setTimeout> | null = null;

  $effect(() => {
    return () => {
      if (searchLinkTimeout) clearTimeout(searchLinkTimeout);
    };
  });

  function copySearchLink() {
    navigator.clipboard.writeText(window.location.href);
    if (searchLinkTimeout) clearTimeout(searchLinkTimeout);
    searchLinkCopied = true;
    searchLinkTimeout = setTimeout(() => {
      searchLinkCopied = false;
      searchLinkTimeout = null;
    }, 1800);
  }

  // "Minhas consultas" (#908) — a saved search is identified by its
  // canonical, pagina-less query (see `searchConsultationId`), so paging
  // through the same search never creates a duplicate entry.
  let savedSearchIds = $state<Set<string>>(new Set());
  let searchSaveNotice = $state<string | null>(null);
  let searchSaveNoticeTimeout: ReturnType<typeof setTimeout> | null = null;

  $effect(() => {
    return () => {
      if (searchSaveNoticeTimeout) clearTimeout(searchSaveNoticeTimeout);
    };
  });

  function readSavedConsultations() {
    return parseSavedConsultations(localStorage.getItem(SAVED_CONSULTATIONS_STORAGE_KEY));
  }

  function refreshSavedSearchIds() {
    savedSearchIds = new Set(
      readSavedConsultations()
        .filter((item) => item.type === 'busca')
        .map((item) => item.id),
    );
  }

  const currentSearchId = $derived(submittedQuery ? searchConsultationId(submittedQuery) : null);
  const isCurrentSearchSaved = $derived(currentSearchId !== null && savedSearchIds.has(currentSearchId));

  function defaultSearchLabel(query: DjenComunicacaoQuery): string {
    const parts = buildCriteriaSummary(query)
      .filter((item) => item.value !== '—' && item.value !== 'Todos')
      .map((item) => item.value);
    return parts.length ? parts.join(' · ') : 'Busca DJEN';
  }

  function toggleSaveSearch() {
    if (!submittedQuery) return;
    const wasSaved = isCurrentSearchSaved;
    const id = searchConsultationId(submittedQuery);
    const items = readSavedConsultations();
    const next = wasSaved
      ? removeSavedConsultation(items, id)
      : saveSearchConsultation(items, submittedQuery, defaultSearchLabel(submittedQuery));
    localStorage.setItem(SAVED_CONSULTATIONS_STORAGE_KEY, serializeSavedConsultations(next));
    refreshSavedSearchIds();

    if (searchSaveNoticeTimeout) clearTimeout(searchSaveNoticeTimeout);
    searchSaveNotice = wasSaved
      ? 'Busca removida de Minhas consultas.'
      : 'Busca salva em Minhas consultas.';
    searchSaveNoticeTimeout = setTimeout(() => {
      searchSaveNotice = null;
      searchSaveNoticeTimeout = null;
    }, 2400);
  }

  function csvField(value: unknown): string {
    const text = value == null ? '' : String(value);
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  }

  function exportCurrentPageCsv() {
    if (!submittedQuery) return;
    const page = submittedQuery.pagina ?? 1;
    const criteria = buildCriteriaSummary(submittedQuery)
      .filter((item) => item.value !== '—' && item.value !== 'Todos')
      .map((item) => `${item.label}: ${item.value}`)
      .join(' · ') || 'sem critério adicional';
    const generatedAt = new Date().toISOString();

    const rows = [
      `# Exportação CausaGanha — página ${page} dos resultados (não é o conjunto completo de ${totalCount} resultado(s))`,
      `# Critério: ${criteria}`,
      `# Gerado em: ${generatedAt}`,
      `# Itens nesta página: ${results.length}`,
      '',
      ['numeroComunicacao', 'siglaTribunal', 'dataDisponibilizacao', 'tipoDocumento', 'orgao', 'texto']
        .map(csvField)
        .join(','),
      ...results.map((pub) =>
        [
          pub.numeroComunicacao,
          pub.siglaTribunal,
          pub.data_disponibilizacao,
          pub.tipoDocumento,
          pub.nomeOrgao,
          pub.texto,
        ]
          .map(csvField)
          .join(','),
      ),
    ];

    const timestampSlug = generatedAt.replace(/[:.]/g, '-');
    const filename = `publicacoes-pagina-${page}-${results.length}-itens-${timestampSlug}.csv`;

    const blob = new Blob([rows.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

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
  const publicationHighlightTerms = $derived([
    submittedQuery?.texto,
    submittedQuery?.nomeParte,
    submittedQuery?.nomeAdvogado,
    submittedQuery?.numeroProcesso,
    submittedQuery?.numeroOab,
  ].filter((term): term is string => typeof term === 'string' && term.trim().length > 1));

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

  const canSubmit = $derived(
    status !== 'loading' &&
      hasPendingInput &&
      queryHasIdentity(effectiveQuery) &&
      cooldownRemaining === 0,
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

  // Sync URL when a search settles, success or failure — a fetch error must
  // not drop the query from a shareable/reloadable URL the way a successful
  // search already preserves it (see status === 'error', which is distinct
  // from an actual absence of results).
  $effect(() => {
    if ((searchQuery.isSuccess || searchQuery.isError) && submittedQuery) {
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
    const current = submittedQuery?.pagina ?? filters.pagina ?? 1;
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
      if (e.defaultPrevented || !(e.ctrlKey || e.metaKey) || e.key.toLowerCase() !== 'k') return;

      e.preventDefault();
      searchInputRef?.focus();
    }
    window.addEventListener('keydown', handleGlobalKeydown);
    return () => {
      window.removeEventListener('keydown', handleGlobalKeydown);
    };
  });

  // Hydrate from URL on mount
  onMount(() => {
    if (typeof window === 'undefined') return;
    refreshSavedSearchIds();
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
    preparedInput = rawInput;
    submitSearch({ resetPage: false });
  });
</script>

<section class="publication-search" aria-labelledby="publication-search-heading">
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

  {#if processoHref}
    <p class="processo-hint" data-tone="info">
      Isto busca só no DJEN. Para ver este processo reconciliado com JURIS (TJRO), STJ e DataJud,
      <a href={processoHref}>abra o dossiê completo →</a>
    </p>
  {/if}

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
        <p>Origem: API DJEN online. A cota é controlada por IP pelo DJEN; tente novamente em <b>{cooldownRemaining}s</b>.</p>
        <p>Alternativa: use o arquivo histórico preservado no Internet Archive, que não consome a cota da busca online.</p>
        <a href={historicalArchiveHref} class="secondary outline" role="button">Usar arquivo histórico</a>
      </div>
    {:else if status === 'error'}
      <div class="alert" data-level="error">
        <strong>Não foi possível buscar.</strong>
        <p>{errorMsg}</p>
        <p>Isso é uma falha de origem, não ausência de resultados — os critérios enviados não foram descartados.</p>
        <div class="empty-search__actions">
          <button type="button" onclick={handleSubmit}>Tentar novamente</button>
          <a href={historicalArchiveHref} class="secondary outline" role="button">Consultar arquivo histórico</a>
        </div>
      </div>
    {:else if status === 'empty'}
      <article class="empty-search" aria-label="Busca sem resultados">
        <strong>Nenhum resultado nesta consulta.</strong>
        <p>
          Isso significa apenas que os critérios enviados não retornaram publicações na cobertura consultada.
          Não prova que a publicação não exista fora do período, do tribunal selecionado ou em uma lacuna de cobertura.
        </p>
        <div class="empty-search__actions">
          <button type="button" class="secondary outline" onclick={() => (showFilters = true)}>
            Revisar filtros
          </button>
          {#if tribunalCoverageHref}
            <a class="secondary outline" role="button" href={tribunalCoverageHref}>
              Ver cobertura de {submittedQuery?.siglaTribunal}
            </a>
          {/if}
          <a class="secondary outline" role="button" href={historicalArchiveHref}>Consultar arquivo histórico</a>
        </div>
      </article>
    {:else if status === 'success'}
      {@const perPage = filters.itensPorPagina ?? 30}
      {@const currentPage = filters.pagina ?? 1}
      {@const totalPages = Math.max(1, Math.ceil(totalCount / perPage))}
      <header id={resultsHeadingId} class="publication-search__results-header">
        <small class="meta-text">{totalCount.toLocaleString('pt-BR')} resultado(s)</small>
        <div class="publication-search__result-actions">
          <button type="button" class="secondary outline" onclick={copySearchLink}>
            {searchLinkCopied ? 'Link copiado' : 'Copiar link desta busca'}
          </button>
          <button
            type="button"
            class="secondary outline"
            onclick={exportCurrentPageCsv}
            title={`Exporta apenas os ${results.length} resultado(s) desta página, não os ${totalCount.toLocaleString('pt-BR')} resultado(s) totais`}
          >
            Exportar CSV (página atual)
          </button>
          <button
            type="button"
            class="secondary outline"
            onclick={toggleSaveSearch}
            title="Guarda esta busca em Minhas consultas, somente neste navegador"
          >
            {isCurrentSearchSaved ? 'Remover de Minhas consultas' : 'Salvar busca'}
          </button>
          {#if searchSaveNotice}
            <span role="status" class="meta-text">{searchSaveNotice}</span>
          {/if}
        </div>
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
              highlightTerms={publicationHighlightTerms}
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
  .processo-hint {
    margin: 0.5rem 0 0;
    font-size: 0.875rem;
    color: var(--fg-muted, var(--color-content-tertiary));
  }

  .publication-search__result-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin: 0.5rem 0;
  }

  .empty-search {
    display: grid;
    gap: 0.75rem;
    padding: 1rem;
    border: 1px solid var(--border, var(--concreto-90, #d8d8d8));
    border-radius: var(--radius, 0.75rem);
    background: var(--papel-20, rgba(0, 0, 0, 0.02));
  }

  .empty-search p {
    margin: 0;
    color: var(--fg-muted, var(--color-content-tertiary));
  }

  .empty-search__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

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