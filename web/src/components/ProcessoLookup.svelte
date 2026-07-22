<script>
  import { onMount } from 'svelte';
  import { getDuckDB } from '../lib/duckdbSingleton';
  import { formatUtcDateTime } from '../lib/data/siteStatus';
  import {
    ALL_FONTES,
    FONTE_LABELS,
    DOCUMENTOS_PAGE_SIZE,
    buildCnjSearchParams,
    buscarProcesso,
    carregarDocumentos,
    classifyCnjInput,
    fontesPresenca,
    formatCnj,
    isDocumentosVazio,
    normalizeCnj,
    readCnjParam,
  } from '../lib/processoCnj';

  let input = $state('');
  let dbStatus = $state('initializing'); // 'initializing' | 'ready' | 'error'
  let dbError = $state(null);

  // 'idle' | 'invalid' | 'querying' | 'not_found' | 'source_unavailable' | 'found'
  let status = $state('idle');
  let invalidMessage = $state(null);
  let queryError = $state(null);
  let processo = $state(null);

  let documentosStatus = $state('idle'); // 'idle' | 'loading' | 'ready' | 'error'
  let documentosError = $state(null);
  let documentos = $state([]);
  let documentosOffset = $state(0);
  let documentosHasMore = $state(false);
  let lastQueriedCnj = $state(null);

  let conn = null;
  let cancelled = false;
  // Monotonic id of the in-flight search. Any async result (processo or
  // documentos) whose captured generation no longer matches the current one
  // belongs to a search the user has since superseded — it's discarded
  // instead of overwriting newer state (see search()/loadDocumentos()).
  let searchGeneration = 0;

  const fontesResumo = $derived(processo ? fontesPresenca(processo.fontes) : null);
  const documentosVazio = $derived(
    status === 'found' && documentosStatus === 'ready' && isDocumentosVazio(documentos, 0) && documentosOffset === 0,
  );
  const datasetGeneratedAtLabel = $derived(
    processo?.datasetGeradoEm ? (formatUtcDateTime(processo.datasetGeradoEm) ?? 'desconhecido') : 'desconhecido',
  );

  async function init() {
    dbStatus = 'initializing';
    dbError = null;
    try {
      const { conn: connInstance } = await getDuckDB();
      if (cancelled) return;
      conn = connInstance;
      dbStatus = 'ready';
    } catch (err) {
      if (cancelled) return;
      dbStatus = 'error';
      dbError = err instanceof Error ? err.message : String(err);
    }
  }

  async function loadDocumentos(digits, offset, generation = searchGeneration) {
    documentosStatus = 'loading';
    documentosError = null;
    try {
      const { items, hasMore } = await carregarDocumentos(
        conn,
        processo?.jurisUrls ?? [],
        processo?.stjUrls ?? [],
        digits,
        offset,
        DOCUMENTOS_PAGE_SIZE,
        processo?.legado ?? false,
      );

      if (generation !== searchGeneration) return; // a newer search superseded this one

      documentos = offset === 0 ? items : [...documentos, ...items];
      documentosHasMore = hasMore;
      documentosOffset = offset;
      documentosStatus = 'ready';
    } catch (err) {
      if (generation !== searchGeneration) return;
      documentosStatus = 'error';
      documentosError = err instanceof Error ? err.message : String(err);
    }
  }

  function loadMoreDocumentos() {
    if (!lastQueriedCnj || documentosStatus === 'loading') return;
    loadDocumentos(lastQueriedCnj, documentosOffset + DOCUMENTOS_PAGE_SIZE);
  }

  async function search(rawInput, { updateUrl = true } = {}) {
    // Every call — including invalid/empty input — claims a new generation,
    // so a still-in-flight older search can never clobber whatever the user
    // triggered next (see the generation checks below and in loadDocumentos).
    const generation = ++searchGeneration;
    const kind = classifyCnjInput(rawInput);

    if (kind === 'empty') {
      status = 'idle';
      return;
    }

    if (kind === 'invalid') {
      status = 'invalid';
      invalidMessage = 'CNJ inválido: cole os 20 dígitos do número do processo, com ou sem máscara (ex.: 0000001-02.2024.8.22.0001).';
      processo = null;
      documentos = [];
      documentosStatus = 'idle';
      return;
    }

    const digits = normalizeCnj(rawInput);

    if (updateUrl && typeof window !== 'undefined') {
      const qs = buildCnjSearchParams(window.location.search, digits);
      const url = `${window.location.pathname}${qs}${window.location.hash}`;
      window.history.replaceState(null, '', url);
    }

    status = 'querying';
    queryError = null;
    processo = null;
    documentos = [];
    documentosStatus = 'idle';
    documentosOffset = 0;
    documentosHasMore = false;

    if (dbStatus !== 'ready') {
      await init();
    }
    if (dbStatus !== 'ready') {
      if (generation !== searchGeneration) return;
      status = 'source_unavailable';
      queryError = dbError ?? 'DuckDB-WASM não inicializou.';
      return;
    }

    try {
      const resultado = await buscarProcesso(conn, digits);

      if (generation !== searchGeneration) return; // a newer search superseded this one

      if (!resultado.encontrado) {
        status = 'not_found';
        lastQueriedCnj = digits;
        return;
      }

      processo = resultado;
      lastQueriedCnj = digits;
      status = 'found';
    } catch (err) {
      if (generation !== searchGeneration) return;
      status = 'source_unavailable';
      queryError = err instanceof Error ? err.message : String(err);
      return;
    }

    // Only reached when the processo query above landed on 'found' for this
    // still-current generation (both 'not_found' and the catch block return
    // earlier). Pin the generation explicitly — a documentos response for a
    // since-superseded search must never land on screen.
    await loadDocumentos(digits, 0, generation);
  }

  function handleSubmit(e) {
    e.preventDefault();
    search(input);
  }

  function retry() {
    if (input.trim()) search(input);
    else init();
  }

  onMount(() => {
    (async () => {
      await init();
      if (cancelled) return;
      const fromUrl = typeof window !== 'undefined' ? readCnjParam(window.location.search) : null;
      if (fromUrl) {
        input = fromUrl;
        await search(fromUrl, { updateUrl: false });
      }
    })();
    return () => {
      cancelled = true;
    };
  });
</script>

<div class="processo-lookup">
  <form onsubmit={handleSubmit} class="processo-lookup__form">
    <label for="processo-cnj-input">Número do processo (CNJ)</label>
    <div class="processo-lookup__row">
      <input
        id="processo-cnj-input"
        type="text"
        bind:value={input}
        placeholder="0000001-02.2024.8.22.0001"
        autocomplete="off"
        spellcheck="false"
        aria-describedby="processo-cnj-hint"
      />
      <button type="submit" aria-busy={status === 'querying'} disabled={status === 'querying'}>
        {status === 'querying' ? 'Consultando…' : 'Buscar'}
      </button>
    </div>
    <small id="processo-cnj-hint" class="meta-text">
      Cole o número com ou sem máscara. A busca roda inteiramente no seu navegador (DuckDB-WASM) —
      nenhum dado é enviado a servidores externos.
    </small>
  </form>

  {#if dbStatus === 'initializing' && status === 'idle'}
    <p aria-busy="true">Inicializando DuckDB-WASM…</p>
  {/if}

  {#if dbStatus === 'error' && status !== 'querying'}
    <article role="alert" data-tone="error">
      <p>Falha ao inicializar DuckDB-WASM: {dbError}</p>
      <p>Tente recarregar a página ou verifique se seu navegador bloqueia Workers/WebAssembly.</p>
      <button class="secondary outline" onclick={retry}>Tentar novamente</button>
    </article>
  {/if}

  {#if status === 'invalid'}
    <aside role="alert" class="alert" data-level="warning">
      <strong>CNJ inválido</strong>
      <p>{invalidMessage}</p>
    </aside>
  {/if}

  {#if status === 'querying'}
    <p aria-busy="true">Consultando indice_processual.parquet e os parquets de origem (DJEN, JURIS, STJ, DataJud) no Internet Archive…</p>
  {/if}

  {#if status === 'not_found'}
    <article class="empty-state">
      <h3>Processo não localizado</h3>
      <p>
        Nenhum registro para <code>{lastQueriedCnj ? formatCnj(lastQueriedCnj) : ''}</code> em
        indice_processual.parquet. Isso significa que o CNJ não apareceu em nenhuma das fontes
        reconciliadas (DJEN, JURIS, STJ, DataJud) até a última geração do dataset — não que o
        processo não existe.
      </p>
    </article>
  {/if}

  {#if status === 'source_unavailable'}
    <article role="alert" data-tone="error">
      <h3>Fonte indisponível</h3>
      <p>Não foi possível consultar o dataset: {queryError}</p>
      <p>Isso costuma indicar uma falha de rede ao buscar o parquet no Internet Archive. Tente novamente.</p>
      <button class="secondary outline" onclick={retry}>Tentar novamente</button>
    </article>
  {/if}

  {#if status === 'found' && processo}
    <section class="processo-dossie" aria-label="Dossiê do processo">
      <header class="processo-dossie__header">
        <h2>{processo.nrProcessoMascara}</h2>
        <p class="meta-text">
          Registros encontrados em {fontesResumo.presentes.length} das {ALL_FONTES.length} fontes consultadas ·
          dataset gerado em {datasetGeneratedAtLabel}
        </p>
      </header>

      {#if processo.avisos.length > 0}
        <aside role="status" class="alert" data-level="warning">
          {#each processo.avisos as aviso}
            <p>{aviso}</p>
          {/each}
        </aside>
      {/if}

      <section aria-labelledby="fontes-title">
        <h3 id="fontes-title">Fontes encontradas</h3>
        <div class="processo-dossie__fontes">
          {#each ALL_FONTES as fonte}
            <span class="badge" data-tone={processo.fontes.includes(fonte) ? 'success' : 'muted'}>
              {FONTE_LABELS[fonte]} {processo.fontes.includes(fonte) ? '✓' : '— sem registro'}
            </span>
          {/each}
        </div>
      </section>

      <article aria-labelledby="datajud-title">
        <header><strong id="datajud-title">Dados cadastrais (DataJud)</strong></header>
        {#if processo.datajud.present}
          <dl>
            <dt>Classe oficial</dt><dd>{processo.datajud.classeOficial ?? '—'}</dd>
            <dt>Assuntos</dt><dd>{processo.datajud.assuntos ?? '—'}</dd>
            <dt>Órgão julgador</dt><dd>{processo.datajud.orgaoJulgador ?? '—'}</dd>
            <dt>Grau</dt><dd>{processo.datajud.grau ?? '—'}</dd>
            <dt>Data de ajuizamento</dt><dd>{processo.datajud.dataAjuizamento ?? '—'}</dd>
            <dt>Última atualização (DataJud)</dt><dd>{processo.datajud.ultimaAtualizacao ?? '—'}</dd>
          </dl>
        {:else}
          <p class="meta-text" data-tone="muted">Sem enriquecimento DataJud para este processo.</p>
        {/if}
      </article>

      <article aria-labelledby="djen-title">
        <header><strong id="djen-title">Comunicações DJEN</strong></header>
        {#if processo.djen.present}
          <dl>
            <dt>Publicações</dt><dd>{processo.djen.nPublicacoes ?? '—'}</dd>
            <dt>Primeira publicação</dt><dd>{processo.djen.primeiraPub ?? '—'}</dd>
            <dt>Última publicação</dt><dd>{processo.djen.ultimaPub ?? '—'}</dd>
            <dt>Tribunais</dt><dd>{processo.djen.tribunais.join(', ') || '—'}</dd>
          </dl>
        {:else}
          <p class="meta-text" data-tone="muted">Sem publicações DJEN para este processo.</p>
        {/if}
      </article>

      <section aria-labelledby="documentos-title">
        <h3 id="documentos-title">Documentos de decisões — JURIS / STJ</h3>

        {#if documentosStatus === 'loading' && documentos.length === 0}
          <p aria-busy="true">Carregando documentos…</p>
        {/if}

        {#if documentosStatus === 'error'}
          <article role="alert" data-tone="error">
            <p>Documentos indisponíveis: {documentosError}</p>
            <button class="secondary outline" onclick={() => loadDocumentos(lastQueriedCnj, 0)}>Tentar novamente</button>
          </article>
        {/if}

        {#if documentosVazio}
          <p class="meta-text" data-tone="muted">
            Nenhum documento de decisão encontrado no JURIS ou no STJ para este processo.
            As publicações do DJEN, quando existentes, aparecem no resumo acima.
          </p>
        {/if}

        {#if documentos.length > 0}
          <ol class="processo-dossie__timeline">
            {#each documentos as doc}
              <li>
                <span class="badge" data-tone="info">{FONTE_LABELS[doc.fonte] ?? doc.fonte}</span>
                <strong>{doc.tipo ?? 'Documento'}</strong>
                <span class="meta-text">{doc.data ?? 'data desconhecida'}</span>
                {#if doc.resumo}<p>{doc.resumo}</p>{/if}
                {#if doc.url}<a href={doc.url} target="_blank" rel="noopener noreferrer">Abrir no portal</a>{/if}
              </li>
            {/each}
          </ol>
          {#if documentosHasMore}
            <button class="outline secondary" onclick={loadMoreDocumentos} disabled={documentosStatus === 'loading'} aria-busy={documentosStatus === 'loading'}>
              {documentosStatus === 'loading' ? 'Carregando…' : 'Carregar mais'}
            </button>
          {/if}
        {/if}
      </section>
    </section>
  {/if}
</div>
