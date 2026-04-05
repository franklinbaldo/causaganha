import { useCallback, useEffect, useRef, useState } from 'preact/hooks';

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

interface QueryResult {
  columns: string[];
  rows: unknown[][];
  rowCount: number;
  duration: number;
}

export function DuckDBExplorer() {
  const [sql, setSql] = useState(QUERY_TEMPLATES[0].sql);
  const [result, setResult] = useState<QueryResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [dbStatus, setDbStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const dbRef = useRef<unknown>(null);
  const connRef = useRef<unknown>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Initialize DuckDB-WASM
  useEffect(() => {
    let cancelled = false;

    async function init() {
      try {
        const duckdb = await import('@duckdb/duckdb-wasm');

        // Use CDN bundles for WASM files
        const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();
        const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);

        const worker = new Worker(bundle.mainWorker!);
        const logger = new duckdb.ConsoleLogger();
        const db = new duckdb.AsyncDuckDB(logger, worker);
        await db.instantiate(bundle.mainModule, bundle.pthreadWorker);

        // Enable httpfs for remote Parquet
        const conn = await db.connect();
        await conn.query("INSTALL httpfs; LOAD httpfs;");
        await conn.query("SET enable_http_metadata_cache=true;");

        if (!cancelled) {
          dbRef.current = db;
          connRef.current = conn;
          setDbStatus('ready');
        }
      } catch (err) {
        if (!cancelled) {
          console.error('DuckDB init failed:', err);
          setDbStatus('error');
          setError(`Falha ao inicializar DuckDB: ${err instanceof Error ? err.message : String(err)}`);
        }
      }
    }

    init();
    return () => { cancelled = true; };
  }, []);

  const runQuery = useCallback(async () => {
    const conn = connRef.current as { query: (sql: string) => Promise<unknown> } | null;
    if (!conn || !sql.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    const start = performance.now();
    try {
      const arrowResult = await conn.query(sql) as {
        schema: { fields: { name: string }[] };
        numRows: number;
        toArray: () => { toJSON: () => Record<string, unknown> }[];
      };
      const duration = Math.round(performance.now() - start);

      const columns = arrowResult.schema.fields.map((f) => f.name);
      const rawRows = arrowResult.toArray();
      const rows = rawRows.map((row) => {
        const obj = row.toJSON();
        return columns.map((col) => obj[col]);
      });

      setResult({
        columns,
        rows,
        rowCount: arrowResult.numRows,
        duration,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, [sql]);

  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      e.preventDefault();
      runQuery();
    }
  }, [runQuery]);

  const exportCsv = useCallback(() => {
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
  }, [result]);

  return (
    <div>
      {/* Status */}
      <div style={{ marginBottom: '1.5rem' }}>
        {dbStatus === 'loading' && (
          <div className="flex items-center gap-2 opacity-70">
            <span className="loading loading-spinner loading-sm text-primary"></span>
            <small>Carregando DuckDB-WASM...</small>
          </div>
        )}
        {dbStatus === 'ready' && (
          <small className="text-success">
            DuckDB pronto — consulte arquivos Parquet diretamente do Internet Archive
          </small>
        )}
        {dbStatus === 'error' && (
          <small className="text-error">
            Erro ao carregar DuckDB-WASM
          </small>
        )}
      </div>

      {/* Query templates */}
      <details style={{ marginBottom: '1.5rem' }}>
        <summary>Consultas de exemplo</summary>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {QUERY_TEMPLATES.map((tmpl) => (
            <button
              key={tmpl.label}
              className="btn btn-outline btn-secondary"
              style={{ textAlign: 'left', fontSize: 'var(--font-size-sm)' }}
              onClick={() => {
                setSql(tmpl.sql);
                setResult(null);
                setError(null);
              }}
            >
              {tmpl.label}
            </button>
          ))}
        </div>
      </details>

      {/* SQL editor */}
      <textarea
        ref={textareaRef}
        className="textarea textarea-bordered"
        value={sql}
        onInput={(e) => setSql((e.target as HTMLTextAreaElement).value)}
        onKeyDown={handleKeyDown}
        rows={8}
        style={{
          fontFamily: 'monospace',
          fontSize: 'var(--font-size-sm)',
          width: '100%',
          resize: 'vertical',
        }}
        placeholder="SELECT * FROM read_parquet('https://archive.org/download/djen-2026-04-01/comunicacoes.parquet') LIMIT 10"
        disabled={dbStatus !== 'ready'}
        aria-label="Editor SQL"
      />

      {/* Action bar */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '2.5rem', alignItems: 'center' }}>
        <button
          className="btn"
          onClick={runQuery}
          disabled={dbStatus !== 'ready' || loading || !sql.trim()}
          aria-busy={loading}
        >
          {loading ? 'Executando...' : 'Executar (Ctrl+Enter)'}
        </button>
        {result && (
          <>
            <button className="btn btn-outline" onClick={exportCsv}>
              Exportar CSV
            </button>
            <small style={{ color: 'var(--color-content-tertiary)' }}>
              {result.rowCount} linha{result.rowCount !== 1 ? 's' : ''} em {result.duration}ms
            </small>
          </>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="card bg-base-100 shadow-sm border border-base-300" style={{ borderLeft: '4px solid var(--color-danger)' }}><div className="card-body" style={{ padding: '1rem' }}>
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: 'var(--font-size-sm)', color: 'var(--color-danger)', margin: 0 }}>
            {error}
          </pre>
        </div></div>
      )}

      {/* Results table */}
      {loading && !result && (
        <div className="table-responsive">
          <table className="table table-zebra table-sm">
            <thead>
              <tr>
                <th><div className="skeleton h-4 w-20"></div></th>
                <th><div className="skeleton h-4 w-32"></div></th>
                <th><div className="skeleton h-4 w-24"></div></th>
              </tr>
            </thead>
            <tbody>
              {[1, 2, 3, 4, 5].map((i) => (
                <tr key={i}>
                  <td><div className="skeleton h-4 w-24 opacity-50"></div></td>
                  <td><div className="skeleton h-4 w-48 opacity-50"></div></td>
                  <td><div className="skeleton h-4 w-16 opacity-50"></div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {result && result.rows.length > 0 && (
        <div className="table-responsive">
          <table className="table table-zebra table-sm table-pin-rows">
            <thead>
              <tr>
                {result.columns.map((col) => (
                  <th key={col}>{col}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {result.rows.slice(0, 500).map((row, i) => (
                <tr key={i} className="hover">
                  {row.map((cell, j) => (
                    <td key={j} style={{ fontSize: 'var(--font-size-sm)', whiteSpace: 'nowrap' }}>
                      {cell === null || cell === undefined ? <em style={{ color: 'var(--color-content-tertiary)' }}>NULL</em> : String(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {result.rows.length > 500 && (
            <small style={{ color: 'var(--color-content-tertiary)' }}>
              Mostrando 500 de {result.rowCount} linhas. Use LIMIT na query para controlar.
            </small>
          )}
        </div>
      )}

      {result && result.rows.length === 0 && (
        <p style={{ color: 'var(--color-content-tertiary)', textAlign: 'center' }}>
          Nenhum resultado retornado.
        </p>
      )}
    </div>
  );
}
