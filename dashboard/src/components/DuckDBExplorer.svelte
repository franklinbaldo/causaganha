<script>
  import { onMount } from 'svelte';

  const IA_BASE = 'https://archive.org/download';

  const QUERY_TEMPLATES = [
    {
      label: 'Comunicações por tribunal (últimos 30 dias)',
      sql: `SELECT tribunal, COUNT(*) as total
FROM read_parquet('${IA_BASE}/djen-2026-04-01/comunicacoes.parquet')
GROUP BY tribunal
ORDER BY total DESC
LIMIT 20`,
    },
    {
      label: 'Advogados mais ativos',
      sql: `SELECT nome, numero_oab, uf_oab, COUNT(*) as comunicacoes
FROM read_parquet('${IA_BASE}/djen-2026-04-01/advogados.parquet') a
JOIN read_parquet('${IA_BASE}/djen-2026-04-01/comunicacao_advogados.parquet') ca
  ON a.id = ca.advogado_id
GROUP BY nome, numero_oab, uf_oab
ORDER BY comunicacoes DESC
LIMIT 20`,
    },
    {
      label: 'Classificações de resultado (keyword_v1)',
      sql: `SELECT outcome, decision_type, COUNT(*) as total, ROUND(AVG(confidence), 2) as avg_confidence
FROM read_parquet('${IA_BASE}/djen-2026-04-01/classificacoes.parquet')
GROUP BY outcome, decision_type
ORDER BY total DESC`,
    },
    {
      label: 'Processos por tribunal',
      sql: `SELECT tribunal, COUNT(DISTINCT numero_processo) as processos
FROM read_parquet('${IA_BASE}/djen-2026-04-01/processos.parquet')
GROUP BY tribunal
ORDER BY processos DESC
LIMIT 20`,
    },
    {
      label: 'Schema das tabelas',
      sql: `DESCRIBE SELECT * FROM read_parquet('${IA_BASE}/djen-2026-04-01/comunicacoes.parquet') LIMIT 0`,
    },
  ];

  let sql = $state(QUERY_TEMPLATES[0].sql);
  let result = $state(null);
  let error = $state(null);
  let loading = $state(false);
  let dbStatus = $state('loading');

  let db = null;
  let conn = null;
  let textareaEl;

  onMount(() => {
    let cancelled = false;

    async function init() {
      try {
        const duckdb = await import('@duckdb/duckdb-wasm');
        console.log('DuckDB components loaded:', !!duckdb);

        const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();
        const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);
        console.log('DuckDB bundle selected:', bundle.mainWorker ? 'Worker ready' : 'No worker');

        if (!bundle.mainWorker) {
          throw new Error('DuckDB bundle selection failed: No mainWorker found.');
        }

        let worker;
        try {
          worker = new Worker(bundle.mainWorker);
        } catch (workerErr) {
          console.warn('Direct Worker load failed, attempting Blob fallback...', workerErr);
          const response = await fetch(bundle.mainWorker);
          const content = await response.text();
          const blob = new Blob([content], { type: 'application/javascript' });
          worker = new Worker(URL.createObjectURL(blob));
        }

        const logger = new duckdb.ConsoleLogger();
        const dbInstance = new duckdb.AsyncDuckDB(logger, worker);
        await dbInstance.instantiate(bundle.mainModule, bundle.pthreadWorker);

        const connInstance = await dbInstance.connect();
        await connInstance.query("INSTALL httpfs; LOAD httpfs;");
        await connInstance.query("SET enable_http_metadata_cache=true;");

        if (!cancelled) {
          db = dbInstance;
          conn = connInstance;
          dbStatus = 'ready';
          console.log('DuckDB-WASM fully initialized.');
        }
      } catch (err) {
        if (!cancelled) {
          console.error('DuckDB init failed:', err);
          dbStatus = 'error';
          const msg = err instanceof Error ? err.message : String(err);
          error = `Falha ao inicializar DuckDB: ${msg}. Verifique se seu navegador bloqueia Workers ou WASM externos.`;
        }
      }
    }

    init();
    return () => { cancelled = true; };
  });

  async function runQuery() {
    if (!conn || !sql.trim()) return;

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
      error = err instanceof Error ? err.message : String(err);
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
    a.download = 'causaganha-query.csv';
    a.click();
    URL.revokeObjectURL(url);
  }
</script>

<div>
  <!-- Status -->
  <div class="mb-6">
    {#if dbStatus === 'loading'}
      <div class="flex items-center gap-2 opacity-70">
        <span class="loading loading-spinner loading-sm text-primary"></span>
        <small>Carregando DuckDB-WASM...</small>
      </div>
    {/if}
    {#if dbStatus === 'ready'}
      <small class="text-success block whitespace-normal leading-tight">
        DuckDB pronto — consulte arquivos Parquet diretamente do Internet Archive
      </small>
    {/if}
    {#if dbStatus === 'error'}
      <small class="text-error block whitespace-normal leading-tight">
        Erro ao carregar DuckDB-WASM
      </small>
    {/if}
  </div>

  <!-- Query templates -->
  <details class="mb-6">
    <summary class="cursor-pointer font-medium hover:underline">Consultas de exemplo</summary>
    <div class="flex flex-col gap-2 mt-2">
      {#each QUERY_TEMPLATES as tmpl}
        <button
          class="btn btn-outline btn-secondary text-left text-sm py-2 h-auto min-h-[3rem]"
          onclick={() => {
            sql = tmpl.sql;
            result = null;
            error = null;
          }}
        >
          {tmpl.label}
        </button>
      {/each}
    </div>
  </details>

  <!-- SQL editor -->
  <textarea
    bind:this={textareaEl}
    class="textarea textarea-bordered font-mono text-sm w-full resize-y min-h-[160px] md:min-h-[200px]"
    bind:value={sql}
    onkeydown={handleKeyDown}
    rows="10"
    placeholder="SELECT * FROM read_parquet('https://archive.org/download/djen-2026-04-01/comunicacoes.parquet') LIMIT 10"
    disabled={dbStatus !== 'ready'}
    aria-label="Editor SQL"
  ></textarea>

  <!-- Action bar -->
  <div class="flex gap-4 mb-10 items-center">
    <button
      class="btn"
      onclick={runQuery}
      disabled={dbStatus !== 'ready' || loading || !sql.trim()}
      aria-busy={loading}
    >
      {loading ? 'Executando...' : 'Executar (Ctrl+Enter)'}
    </button>
    {#if result}
      <button class="btn btn-outline" onclick={exportCsv}>
        Exportar CSV
      </button>
      <small class="opacity-50">
        {result.rowCount} linha{result.rowCount !== 1 ? 's' : ''} em {result.duration}ms
      </small>
    {/if}
  </div>

  <!-- Error -->
  {#if error}
    <div class="card bg-base-100 shadow-sm border border-base-300 border-l-4 border-error"><div class="card-body p-4">
      <pre class="whitespace-pre-wrap text-sm text-error m-0">{error}</pre>
    </div></div>
  {/if}

  <!-- Results table -->
  {#if loading && !result}
    <div class="table-responsive">
      <table class="table table-zebra table-sm">
        <thead>
          <tr>
            <th><div class="skeleton h-4 w-20"></div></th>
            <th><div class="skeleton h-4 w-32"></div></th>
            <th><div class="skeleton h-4 w-24"></div></th>
          </tr>
        </thead>
        <tbody>
          {#each [1, 2, 3, 4, 5] as i}
            <tr>
              <td><div class="skeleton h-4 w-24 opacity-50"></div></td>
              <td><div class="skeleton h-4 w-48 opacity-50"></div></td>
              <td><div class="skeleton h-4 w-16 opacity-50"></div></td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}

  {#if result && result.rows.length > 0}
    <div class="table-responsive">
      <table class="table table-zebra table-sm table-pin-rows">
        <thead>
          <tr>
            {#each result.columns as col}
              <th>{col}</th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each result.rows.slice(0, 500) as row, i}
            <tr class="hover">
              {#each row as cell, j}
                <td class="text-sm whitespace-nowrap">
                  {#if cell === null || cell === undefined}
                    <em class="opacity-50">NULL</em>
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
        <small class="opacity-50">
          Mostrando 500 de {result.rowCount} linhas. Use LIMIT na query para controlar.
        </small>
      {/if}
    </div>
  {/if}

  {#if result && result.rows.length === 0}
    <p class="opacity-50 text-center">
      Nenhum resultado retornado.
    </p>
  {/if}
</div>
