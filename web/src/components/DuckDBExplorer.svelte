<script>
  import { onMount } from 'svelte';
  import { getDuckDB } from '../lib/duckdbSingleton';

  const IA_BASE = 'https://archive.org/download';

  // Per-(tribunal, year) IA items hold the consolidated parquets.
  // Pick any tribunal/year — TJRO 2026 used here as a demo.
  const ITEM = 'djen-tjro-2026';

  const QUERY_TEMPLATES = [
    {
      label: 'Comunicações por órgão (TJRO 2026)',
      sql: `SELECT nome_orgao, COUNT(*) as total
FROM read_parquet('${IA_BASE}/${ITEM}/comunicacoes.parquet')
GROUP BY nome_orgao
ORDER BY total DESC
LIMIT 20`,
    },
    {
      label: 'Advogados mais ativos (TJRO 2026)',
      sql: `SELECT nome, numero_oab, uf_oab, COUNT(*) as comunicacoes
FROM read_parquet('${IA_BASE}/${ITEM}/advogados.parquet') a
JOIN read_parquet('${IA_BASE}/${ITEM}/comunicacao_advogados.parquet') ca
  ON a.id = ca.advogado_id
GROUP BY nome, numero_oab, uf_oab
ORDER BY comunicacoes DESC
LIMIT 20`,
    },
    {
      label: 'Classificações de resultado (keyword_v1)',
      sql: `SELECT outcome, decision_type, COUNT(*) as total, ROUND(AVG(confidence), 2) as avg_confidence
FROM read_parquet('${IA_BASE}/${ITEM}/classificacoes.parquet')
GROUP BY outcome, decision_type
ORDER BY total DESC`,
    },
    {
      label: 'Processos distintos (TJRO 2026)',
      sql: `SELECT COUNT(DISTINCT numero_processo) as processos
FROM read_parquet('${IA_BASE}/${ITEM}/comunicacoes.parquet')`,
    },
    {
      label: 'Schema das tabelas',
      sql: `DESCRIBE SELECT * FROM read_parquet('${IA_BASE}/${ITEM}/comunicacoes.parquet') LIMIT 0`,
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
  let cancelled = false;

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

  onMount(() => {
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
  <div class="status-section">
    {#if dbStatus === 'loading'}
      <div class="status-loading">
        <span class="spinner"></span>
        <small>Carregando DuckDB-WASM...</small>
      </div>
    {/if}
    {#if dbStatus === 'ready'}
      <small class="status-ready">
        DuckDB pronto — consulte arquivos Parquet diretamente do Internet Archive
      </small>
    {/if}
    {#if dbStatus === 'error'}
      <div class="status-error-card">
        <p class="status-error-msg">{error ?? 'Falha ao inicializar DuckDB-WASM.'}</p>
        <p class="status-error-hint">
          Tente recarregar a página. Se o problema persistir, verifique se seu navegador
          suporta WebAssembly e se extensões de bloqueio não estão impedindo Workers externos.
        </p>
        <button class="retry-btn" onclick={() => { error = null; init(); }}>
          Tentar novamente
        </button>
      </div>
    {/if}
  </div>

  <!-- Starter cards -->
  <div class="starter-cards" aria-label="Consultas de exemplo">
    {#each QUERY_TEMPLATES.slice(0, 3) as tmpl}
      <button
        class="starter-card"
        onclick={() => { sql = tmpl.sql; result = null; error = null; }}
        disabled={dbStatus !== 'ready'}
      >
        <span class="starter-card-label">{tmpl.label}</span>
        <span class="starter-card-hint" aria-hidden="true">Clique para carregar →</span>
      </button>
    {/each}
  </div>
  <!-- Additional templates -->
  <details class="templates-more">
    <summary class="templates-more-summary">Ver mais consultas de exemplo</summary>
    <div class="templates-list">
      {#each QUERY_TEMPLATES.slice(3) as tmpl}
        <button
          class="template-btn"
          onclick={() => { sql = tmpl.sql; result = null; error = null; }}
          disabled={dbStatus !== 'ready'}
        >
          {tmpl.label}
        </button>
      {/each}
    </div>
  </details>

  <!-- SQL editor -->
  <textarea
    bind:this={textareaEl}
    class="sql-editor"
    bind:value={sql}
    onkeydown={handleKeyDown}
    rows="10"
    placeholder="SELECT * FROM read_parquet('https://archive.org/download/djen-tjro-2026/comunicacoes.parquet') LIMIT 10"
    disabled={dbStatus !== 'ready'}
    aria-label="Editor SQL"
  ></textarea>

  <!-- Action bar -->
  <div class="action-bar">
    <button
      onclick={runQuery}
      disabled={dbStatus !== 'ready' || loading || !sql.trim()}
      aria-busy={loading}
    >
      {loading ? 'Executando...' : 'Executar (Ctrl+Enter)'}
    </button>
    {#if result}
      <button class="outline secondary" onclick={exportCsv}>
        Exportar CSV
      </button>
      <small class="result-meta">
        {result.rowCount.toLocaleString('pt-BR')} linha{result.rowCount !== 1 ? 's' : ''} em {result.duration.toLocaleString('pt-BR')}ms
      </small>
    {/if}
  </div>

  <!-- Error -->
  {#if error}
    <div class="error-card"><div class="error-card-body">
      <pre class="error-pre">{error}</pre>
    </div></div>
  {/if}

  <!-- Results table -->
  {#if loading && !result}
    <div class="table-responsive">
      <table class="data-table">
        <thead>
          <tr>
            <th><div class="skeleton skeleton--w20"></div></th>
            <th><div class="skeleton skeleton--w32"></div></th>
            <th><div class="skeleton skeleton--w24"></div></th>
          </tr>
        </thead>
        <tbody>
          {#each [1, 2, 3, 4, 5] as i}
            <tr>
              <td><div class="skeleton skeleton--w24 skeleton--dim"></div></td>
              <td><div class="skeleton skeleton--w48 skeleton--dim"></div></td>
              <td><div class="skeleton skeleton--w16 skeleton--dim"></div></td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/if}

  {#if result && result.rows.length > 0}
    <div class="table-responsive">
      <table class="data-table data-table--pinned">
        <thead>
          <tr>
            {#each result.columns as col}
              <th>{col}</th>
            {/each}
          </tr>
        </thead>
        <tbody>
          {#each result.rows.slice(0, 500) as row, i}
            <tr class="data-row">
              {#each row as cell, j}
                <td class="data-cell">
                  {#if cell === null || cell === undefined}
                    <em class="null-value">NULL</em>
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
        <small class="truncation-notice">
          Mostrando 500 de {result.rowCount.toLocaleString('pt-BR')} linhas. Use LIMIT na query para controlar.
        </small>
      {/if}
    </div>
  {/if}

  {#if result && result.rows.length === 0}
    <p class="empty-result">
      Nenhum resultado retornado.
    </p>
  {/if}
</div>
