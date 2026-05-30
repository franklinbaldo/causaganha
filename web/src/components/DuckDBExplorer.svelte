<script>
  import { onMount } from 'svelte';
  import { getDuckDB } from '../lib/duckdbSingleton';

  const IA_BASE = 'https://archive.org/download';
  const CURRENT_YEAR = new Date().getUTCFullYear();
  const DEFAULT_YEARS = [CURRENT_YEAR, CURRENT_YEAR - 1, CURRENT_YEAR - 2].filter((year) => year >= 2020);

  const TABLES = [
    {
      key: 'comunicacoes',
      file: 'comunicacoes.parquet',
      label: 'comunicações',
      description: 'Intimações e comunicações judiciais publicadas no DJEN.',
    },
    {
      key: 'advogados',
      file: 'advogados.parquet',
      label: 'advogados',
      description: 'Advogados identificados nas comunicações, com OAB e UF quando disponíveis.',
    },
    {
      key: 'vinculos',
      file: 'comunicacao_advogados.parquet',
      label: 'vínculos',
      description: 'Relações entre comunicações, advogados, partes e representações.',
    },
    {
      key: 'classificacoes',
      file: 'classificacoes.parquet',
      label: 'classificações',
      description: 'Classificações de resultado e tipo de decisão geradas pelo pipeline.',
    },
  ];

  const TEMPLATE_DEFINITIONS = [
    {
      label: 'Comunicações por órgão',
      description: 'Conta as comunicações por órgão julgador no dataset selecionado.',
      sql: (path) => `SELECT nome_orgao, COUNT(*) as total
FROM read_parquet('${path('comunicacoes.parquet')}')
GROUP BY nome_orgao
ORDER BY total DESC
LIMIT 20`,
    },
    {
      label: 'Advogados mais ativos',
      description: 'Cruza advogados com vínculos de comunicação para ranquear por volume.',
      sql: (path) => `SELECT nome, numero_oab, uf_oab, COUNT(*) as comunicacoes
FROM read_parquet('${path('advogados.parquet')}') a
JOIN read_parquet('${path('comunicacao_advogados.parquet')}') ca
  ON a.id = ca.advogado_id
GROUP BY nome, numero_oab, uf_oab
ORDER BY comunicacoes DESC
LIMIT 20`,
    },
    {
      label: 'Classificações de resultado',
      description: 'Agrupa resultados classificados e exibe confiança média.',
      sql: (path) => `SELECT outcome, decision_type, COUNT(*) as total, ROUND(AVG(confidence), 2) as avg_confidence
FROM read_parquet('${path('classificacoes.parquet')}')
GROUP BY outcome, decision_type
ORDER BY total DESC`,
    },
    {
      label: 'Processos distintos',
      description: 'Conta processos únicos nas comunicações.',
      sql: (path) => `SELECT COUNT(DISTINCT numero_processo) as processos
FROM read_parquet('${path('comunicacoes.parquet')}')`,
    },
    {
      label: 'Schema de comunicações',
      description: 'Inspeciona as colunas de comunicações sem carregar linhas.',
      sql: (path) => `DESCRIBE SELECT * FROM read_parquet('${path('comunicacoes.parquet')}') LIMIT 0`,
    },
  ];

  let { publicBase = '/' } = $props();

  let sql = $state('');
  let result = $state(null);
  let error = $state(null);
  let loading = $state(false);
  let dbStatus = $state('loading');
  let selectedTribunal = $state('');
  let selectedYear = $state('');
  let startDates = $state({});
  let metadataError = $state(null);
  let datasetStatus = $state('idle');
  let datasetError = $state(null);
  let datasetFiles = $state([]);

  let db = null;
  let conn = null;
  let textareaEl;
  let cancelled = false;
  const datasetCache = new Map();

  const normalizedBase = $derived(publicBase.replace(/\/?$/, '/'));
  const tribunals = $derived(Object.keys(startDates).sort((a, b) => a.localeCompare(b, 'pt-BR')));
  const hasDatasetSelection = $derived(Boolean(selectedTribunal && selectedYear));
  const itemId = $derived(hasDatasetSelection ? `djen-${selectedTribunal.toLowerCase()}-${selectedYear}` : '');
  const datasetBaseUrl = $derived(itemId ? `${IA_BASE}/${itemId}` : '');
  const yearOptions = $derived(getYearOptions(selectedTribunal));
  const availableFileNames = $derived(new Set(datasetFiles.map((file) => file.name)));
  const tableList = $derived(TABLES.map((table) => ({
    ...table,
    available: datasetStatus === 'ready' ? availableFileNames.has(table.file) : null,
  })));
  const queryTemplates = $derived(hasDatasetSelection ? buildTemplates() : []);
  const suggestedTribunals = $derived(tribunals.slice(0, 8).join(', '));
  const suggestedYears = $derived(selectedTribunal ? getYearOptions(selectedTribunal).join(', ') : DEFAULT_YEARS.join(', '));

  function getYearOptions(tribunal) {
    const startDate = startDates[tribunal];
    if (!startDate) return DEFAULT_YEARS;

    const startYear = Number(String(startDate).slice(0, 4));
    if (!Number.isFinite(startYear)) return DEFAULT_YEARS;

    const years = [];
    for (let year = CURRENT_YEAR; year >= startYear; year -= 1) {
      years.push(year);
    }
    return years;
  }

  function parquetPath(fileName) {
    return `${datasetBaseUrl}/${fileName}`;
  }

  function buildTemplates() {
    return TEMPLATE_DEFINITIONS.map((template) => ({
      ...template,
      sql: template.sql(parquetPath),
    }));
  }

  function applyTemplate(template) {
    sql = template.sql;
    result = null;
    error = null;
  }

  function describeMissingDataset() {
    const tribunalPart = selectedTribunal
      ? `Para ${selectedTribunal}, tente um destes anos: ${suggestedYears}.`
      : `Tribunais sugeridos: ${suggestedTribunals}.`;

    return `Dataset ${itemId || '(sem seleção)'} não encontrado no Internet Archive. ${tribunalPart} Também é possível trocar o tribunal no seletor acima.`;
  }

  async function init() {
    dbStatus = 'loading';
    try {
      const { db: dbInstance, conn: connInstance } = await getDuckDB();

      if (!cancelled) {
        db = dbInstance;
        conn = connInstance;
        dbStatus = 'ready';
      }
    } catch (err) {
      if (!cancelled) {
        dbStatus = 'error';
        const msg = err instanceof Error ? err.message : String(err);
        error = `Falha ao inicializar DuckDB: ${msg}`;
      }
    }
  }

  async function loadStartDates() {
    try {
      const response = await fetch(`${normalizedBase}tribunal_start_dates.json`);
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      startDates = await response.json();
    } catch (err) {
      metadataError = err instanceof Error ? err.message : String(err);
      startDates = { TJRO: '2024-01-01', STJ: '2024-11-21', TST: '2024-06-11' };
    }
  }

  onMount(() => {
    init();
    loadStartDates();
    return () => { cancelled = true; };
  });

  $effect(() => {
    if (selectedTribunal && selectedYear && !yearOptions.includes(Number(selectedYear))) {
      selectedYear = '';
      sql = '';
    }
  });

  $effect(() => {
    if (!hasDatasetSelection) {
      datasetStatus = 'idle';
      datasetError = null;
      datasetFiles = [];
      return;
    }

    let active = true;

    async function validateDataset() {
      datasetStatus = 'checking';
      datasetError = null;
      datasetFiles = [];

      if (datasetCache.has(itemId)) {
        const cached = datasetCache.get(itemId);
        if (!active) return;
        datasetStatus = cached.status;
        datasetFiles = cached.files;
        datasetError = cached.error;
        return;
      }

      try {
        const response = await fetch(`https://archive.org/metadata/${itemId}/files`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        const data = await response.json();
        const files = (data?.result || data || [])
          .filter((file) => file?.name?.endsWith('.parquet'))
          .map((file) => ({ name: file.name, size: Number(file.size) || 0 }));

        if (files.length === 0) throw new Error('Nenhum arquivo Parquet encontrado');

        const value = { status: 'ready', files, error: null };
        datasetCache.set(itemId, value);
        if (!active) return;
        datasetStatus = value.status;
        datasetFiles = value.files;
        datasetError = value.error;
      } catch (err) {
        const value = { status: 'missing', files: [], error: describeMissingDataset() };
        datasetCache.set(itemId, value);
        if (!active) return;
        datasetStatus = value.status;
        datasetFiles = value.files;
        datasetError = value.error;
      }
    }

    validateDataset();
    return () => { active = false; };
  });

  async function runQuery() {
    if (!conn || !sql.trim()) return;

    if (!hasDatasetSelection) {
      error = 'Escolha um tribunal e ano para começar.';
      return;
    }

    if (datasetStatus === 'missing') {
      error = datasetError ?? describeMissingDataset();
      return;
    }

    loading = true;
    error = null;
    result = null;

    const start = performance.now();
    try {
      const arrowResult = await conn.query(sql);
      const duration = Math.round(performance.now() - start);

      const columns = arrowResult.schema.fields.map((f) => f.name);
      const rawRows = arrowResult.toArray();
      const rows = rawRows.map((row) => {
        const obj = row.toJSON();
        return columns.map((col) => obj[col]);
      });

      result = {
        columns,
        rows,
        rowCount: arrowResult.numRows,
        duration,
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      error = message.includes(itemId) || message.includes('HTTP')
        ? `${message}\n\n${describeMissingDataset()}`
        : message;
    } finally {
      loading = false;
    }
  }

  function handleKeyDown(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      runQuery();
    }
  }

  function exportCsv() {
    if (!result) return;
    const header = result.columns.join(',');
    const rows = result.rows.map((row) =>
      row.map((cell) => {
        const str = String(cell ?? '');
        return str.includes(',') || str.includes('"') || str.includes('\n')
          ? `"${str.replace(/"/g, '""')}"`
          : str;
      }).join(',')
    );
    const csv = [header, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `causaganha-${itemId || 'query'}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }
</script>

<div>
  <!-- Status -->
  <div>
    {#if dbStatus === 'loading'}
      <p aria-busy="true">Carregando DuckDB-WASM...</p>
    {/if}
    {#if dbStatus === 'ready'}
      <small>
        DuckDB pronto — consulte arquivos Parquet diretamente do Internet Archive
      </small>
    {/if}
    {#if dbStatus === 'error'}
      <article role="alert" data-tone="error">
        <p>{error ?? 'Falha ao inicializar DuckDB-WASM.'}</p>
        <p>
          Tente recarregar a página. Se o problema persistir, verifique se seu navegador
          suporta WebAssembly e se extensões de bloqueio não estão impedindo Workers externos.
        </p>
        <button class="secondary outline" onclick={() => { error = null; init(); }}>
          Tentar novamente
        </button>
      </article>
    {/if}
  </div>

  <!-- Dataset selectors -->
  <section aria-labelledby="dataset-selector-title">
    <h3 id="dataset-selector-title">Escolha o dataset</h3>
    <div class="grid">
      <label>
        Tribunal
        <select bind:value={selectedTribunal} disabled={tribunals.length === 0} aria-label="Tribunal">
          <option value="">Selecione um tribunal</option>
          {#each tribunals as tribunal}
            <option value={tribunal}>{tribunal}</option>
          {/each}
        </select>
      </label>
      <label>
        Ano
        <select bind:value={selectedYear} disabled={!selectedTribunal} aria-label="Ano">
          <option value="">Selecione um ano</option>
          {#each yearOptions as year}
            <option value={String(year)}>{year}</option>
          {/each}
        </select>
      </label>
    </div>
    {#if metadataError}
      <small data-tone="muted">
        Não foi possível carregar todos os metadados de início ({metadataError}); exibindo opções mínimas.
      </small>
    {/if}
    {#if hasDatasetSelection}
      <small class="meta-text">
        Dataset selecionado: <code>{itemId}</code> · caminhos gerados em <code>{datasetBaseUrl}/&lt;tabela&gt;.parquet</code>
      </small>
    {/if}
  </section>

  {#if !hasDatasetSelection}
    <article>
      <h3>Escolha um tribunal e ano para começar</h3>
      <p>
        Depois da seleção, o explorador gera automaticamente os caminhos
        <code>read_parquet(...)</code>, habilita templates parametrizados e valida se o item existe no Internet Archive.
      </p>
    </article>
  {:else}
    {#if datasetStatus === 'checking'}
      <p aria-busy="true">Verificando dataset no Internet Archive...</p>
    {/if}
    {#if datasetStatus === 'missing'}
      <article role="alert" data-tone="error">
        <p>{datasetError}</p>
      </article>
    {/if}

    <!-- Available tables -->
    <section aria-labelledby="available-tables-title">
      <h3 id="available-tables-title">Tabelas disponíveis</h3>
      <div class="auto-grid">
        {#each tableList as table}
          <article>
            <strong>{table.label}</strong>
            <p>{table.description}</p>
            <small>
              <code>{table.file}</code>
              {#if table.available === true}
                · disponível
              {:else if table.available === false}
                · não encontrado neste dataset
              {/if}
            </small>
          </article>
        {/each}
      </div>
    </section>

    <!-- Starter cards -->
    <div class="auto-grid" aria-label="Consultas de exemplo">
      {#each queryTemplates.slice(0, 3) as tmpl}
        <button
          class="outline"
          onclick={() => applyTemplate(tmpl)}
          disabled={dbStatus !== 'ready' || datasetStatus !== 'ready'}
        >
          <strong>{tmpl.label}</strong>
          <small>{tmpl.description}</small>
        </button>
      {/each}
    </div>
    <!-- Additional templates -->
    <details>
      <summary>Ver mais consultas de exemplo</summary>
      <div>
        {#each queryTemplates.slice(3) as tmpl}
          <button
            class="secondary"
            onclick={() => applyTemplate(tmpl)}
            disabled={dbStatus !== 'ready' || datasetStatus !== 'ready'}
          >
            {tmpl.label}
          </button>
        {/each}
      </div>
    </details>
  {/if}

  <!-- SQL editor -->
  <textarea
    bind:this={textareaEl}
    bind:value={sql}
    onkeydown={handleKeyDown}
    rows="10"
    placeholder={hasDatasetSelection ? `SELECT * FROM read_parquet('${datasetBaseUrl}/comunicacoes.parquet') LIMIT 10` : 'Escolha um tribunal e ano para gerar os caminhos read_parquet(...)'}
    disabled={dbStatus !== 'ready' || !hasDatasetSelection || datasetStatus !== 'ready'}
    aria-label="Editor SQL"
  ></textarea>

  <!-- Action bar -->
  <div>
    <button
      onclick={runQuery}
      disabled={dbStatus !== 'ready' || loading || !sql.trim() || !hasDatasetSelection || datasetStatus !== 'ready'}
      aria-busy={loading}
    >
      {loading ? 'Executando...' : 'Executar (Ctrl+Enter)'}
    </button>
    {#if result}
      <button class="outline secondary" onclick={exportCsv}>
        Exportar CSV
      </button>
      <small class="meta-text">
        {result.rowCount.toLocaleString('pt-BR')} linha{result.rowCount !== 1 ? 's' : ''} em {result.duration.toLocaleString('pt-BR')}ms
      </small>
    {/if}
  </div>

  <!-- Error -->
  {#if error}
    <article role="alert" data-tone="error">
      <pre><code>{error}</code></pre>
    </article>
  {/if}

  <!-- Results table -->
  {#if loading && !result}
    <p aria-busy="true">Carregando...</p>
  {/if}

  {#if result && result.rows.length > 0}
    <div class="table-responsive">
      <table class="striped">
        <thead>
          <tr>
            {#each result.columns as col}
              <th>{col}</th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each result.rows.slice(0, 500) as row, i}
            <tr>
              {#each row as cell, j}
                <td>
                  {#if cell === null || cell === undefined}
                    <small data-tone="muted">NULL</small>
                  {:else}
                    {String(cell)}
                  {/if}
                </td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
      {#if result.rows.length > 500}
        <small class="meta-text">
          Mostrando 500 de {result.rowCount.toLocaleString('pt-BR')} linhas. Use LIMIT na query para controlar.
        </small>
      {/if}
    </div>
  {/if}

  {#if result && result.rows.length === 0}
    <p class="meta-text">
      Nenhum resultado retornado.
    </p>
  {/if}
</div>
