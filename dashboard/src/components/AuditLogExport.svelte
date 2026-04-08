<script>
  import { onMount } from 'svelte';

  let loading = $state(false);
  let status = $state('idle'); // idle, loading-db, ready, error
  let errorMsg = $state('');

  let db = null;
  let conn = null;

  // Date filters
  let endDate = $state(new Date().toISOString().split('T')[0]);
  let startDate = $state(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]);

  onMount(() => {
    let cancelled = false;

    async function init() {
      status = 'loading-db';
      try {
        const duckdb = await import('@duckdb/duckdb-wasm');
        const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();
        const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);

        if (!bundle.mainWorker) {
          throw new Error('No mainWorker found for DuckDB.');
        }

        let worker;
        try {
          worker = new Worker(bundle.mainWorker);
        } catch (workerErr) {
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
          status = 'ready';
        }
      } catch (err) {
        if (!cancelled) {
          status = 'error';
          errorMsg = err instanceof Error ? err.message : String(err);
        }
      }
    }

    init();
    return () => { cancelled = true; };
  });

  async function exportAuditLog() {
    if (!conn) return;

    loading = true;
    errorMsg = '';

    try {
      const query = `
        SELECT date, tribunal, file_type, duration_s, ia_url
        FROM read_parquet('https://archive.org/download/causaganha-catalog/manifest.parquet')
        WHERE TRY_CAST(date AS DATE) >= '${startDate}'
          AND TRY_CAST(date AS DATE) <= '${endDate}'
        ORDER BY date DESC, tribunal ASC
      `;

      const arrowResult = await conn.query(query);
      const columns = arrowResult.schema.fields.map(f => f.name);
      const rawRows = arrowResult.toArray();

      const rows = rawRows.map(row => {
        const obj = row.toJSON();
        return columns.map(col => obj[col]);
      });

      const header = columns.join(',');
      const csvRows = rows.map(row =>
        row.map(cell => {
          const str = String(cell ?? '');
          return str.includes(',') || str.includes('"') || str.includes('\n')
            ? `"${str.replace(/"/g, '""')}"`
            : str;
        }).join(',')
      );

      const csv = [header, ...csvRows].join('\n');
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);

      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_log_${startDate}_to_${endDate}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

    } catch (err) {
      errorMsg = err instanceof Error ? err.message : String(err);
    } finally {
      loading = false;
    }
  }
</script>

<div class="card bg-base-100 shadow-sm border border-base-300">
  <div class="card-body p-6">
    <h2 class="card-title text-xl mb-4">Export Audit Log (CSV)</h2>
    <p class="text-sm opacity-70 mb-4">
      Export pipeline history directly from the catalog's manifest.parquet.
    </p>

    {#if status === 'loading-db'}
      <div class="alert alert-info">Carregando engine DuckDB...</div>
    {:else if status === 'error'}
      <div class="alert alert-error">Erro ao carregar DuckDB: {errorMsg}</div>
    {:else if status === 'ready'}
      <div class="flex flex-col md:flex-row gap-4 mb-4 items-end">
        <div class="form-control">
          <label class="label"><span class="label-text">Data Inicial</span></label>
          <input type="date" bind:value={startDate} class="input input-bordered" />
        </div>
        <div class="form-control">
          <label class="label"><span class="label-text">Data Final</span></label>
          <input type="date" bind:value={endDate} class="input input-bordered" />
        </div>
        <button
          class="btn btn-primary"
          onclick={exportAuditLog}
          disabled={loading}
          aria-busy={loading}
        >
          {loading ? 'Exportando...' : 'Exportar CSV'}
        </button>
      </div>

      {#if errorMsg}
        <div class="alert alert-error mt-4">{errorMsg}</div>
      {/if}
    {/if}
  </div>
</div>
