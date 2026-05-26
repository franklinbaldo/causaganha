<script lang="ts">
  import { onMount } from 'svelte';
  import { fetchWithRetry } from '../lib/fetchData';

  let loading = $state(false);
  let status = $state('idle'); // idle, loading-db, ready, error
  let errorMsg = $state('');

  let db = $state<any>(null);
  let conn = $state<any>(null);

  // Date filters
  let endDate = $state(new Date().toISOString().split('T')[0]);
  let startDate = $state(new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]);

  onMount(() => {
    let cancelled = false;

    async function init() {
      status = 'loading-db';
      try {
        const { db: dbInstance, conn: connInstance } = await import('../lib/duckdbSingleton').then(m => m.getDuckDB());

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

<article>
  <h2>Export Audit Log (CSV)</h2>
  <p>
    Export pipeline history directly from the catalog's manifest.parquet.
  </p>

  {#if status === 'loading-db'}
    <p aria-live="polite" aria-busy="true">Carregando engine DuckDB...</p>
  {:else if status === 'error'}
    <aside role="alert" class="alert" data-level="error">Erro ao carregar DuckDB: {errorMsg}</aside>
  {:else if status === 'ready'}
    <fieldset role="group">
      <label>
        Data Inicial
        <input type="date" bind:value={startDate} />
      </label>
      <label>
        Data Final
        <input type="date" bind:value={endDate} />
      </label>
      <button onclick={exportAuditLog} disabled={loading} aria-busy={loading}>
        {loading ? 'Exportando...' : 'Exportar CSV'}
      </button>
    </fieldset>

    {#if errorMsg}
      <aside role="alert" class="alert" data-level="error">{errorMsg}</aside>
    {/if}
  {/if}
</article>
