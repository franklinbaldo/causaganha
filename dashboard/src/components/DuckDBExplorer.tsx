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
        console.log('DuckDB components loaded:', !!duckdb);

        // Get bundles (using CDN for simplicity/zero-config)
        const JSDELIVR_BUNDLES = duckdb.getJsDelivrBundles();
        const bundle = await duckdb.selectBundle(JSDELIVR_BUNDLES);
        console.log('DuckDB bundle selected:', bundle.mainWorker ? 'Worker ready' : 'No worker');

        if (!bundle.mainWorker) {
          throw new Error('DuckDB bundle selection failed: No mainWorker found.');
        }

        // Initialize worker (may fail due to CSP/CORS)
        let worker: Worker;
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
          console.log('DuckDB-WASM fully initialized.');
        }
      } catch (err) {
        if (!cancelled) {
          console.error('DuckDB init failed:', err);
          setDbStatus('error');
          const msg = err instanceof Error ? err.message : String(err);
          setError(`Falha ao inicializar DuckDB: ${msg}. Verifique se seu navegador bloqueia Workers ou WASM externos.`);
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
      <div className="mb-6">
        {dbStatus === 'loading' && (
          <div className="flex items-center gap-2 opacity-70">
            <span className="loading loading-spinner loading-sm text-primary"></span>
            <small>Carregando DuckDB-WASM...</small>
          </div>
        )}
        {dbStatus === 'ready' && (
          <small className="text-success block whitespace-normal leading-tight">
            DuckDB pronto — consulte arquivos Parquet diretamente do Internet Archive
          </small>
        )}
        {dbStatus === 'error' && (
          <small className="text-error block whitespace-normal leading-tight">
            Erro ao carregar DuckDB-WASM
          </small>
        )}
      </div>

      {/* Query templates */}
      <details className="mb-6">
        <summary className="cursor-pointer font-medium hover:underline">Consultas de exemplo</summary>
        <div className="flex flex-col gap-2 mt-2">
          {QUERY_TEMPLATES.map((tmpl) => (
            <button
              key={tmpl.label}
              className="btn btn-outline btn-secondary text-left text-sm py-2 h-auto min-h-[3rem]"
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
        className="textarea textarea-bordered font-mono text-sm w-full resize-y min-h-[160px] md:min-h-[200px]"
        value={sql}
        onInput={(e) => setSql((e.target as HTMLTextAreaElement).value)}
        onKeyDown={handleKeyDown}
        rows={10}
        placeholder="SELECT * FROM read_parquet('https://archive.org/download/djen-2026-04-01/comunicacoes.parquet') LIMIT 10"
        disabled={dbStatus !== 'ready'}
        aria-label="Editor SQL"
      />

      {/* Action bar */}
      <div className="flex gap-4 mb-10 items-center">
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
            <small className="opacity-50">
              {result.rowCount} linha{result.rowCount !== 1 ? 's' : ''} em {result.duration}ms
            </small>
          </>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="card bg-base-100 shadow-sm border border-base-300 border-l-4 border-error"><div className="card-body p-4">
          <pre className="whitespace-pre-wrap text-sm text-error m-0">
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
                    <td key={j} className="text-sm whitespace-nowrap">
                      {cell === null || cell === undefined ? <em className="opacity-50">NULL</em> : String(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {result.rows.length > 500 && (
            <small className="opacity-50">
              Mostrando 500 de {result.rowCount} linhas. Use LIMIT na query para controlar.
            </small>
          )}
        </div>
      )}

      {result && result.rows.length === 0 && (
        <p className="opacity-50 text-center">
          Nenhum resultado retornado.
        </p>
      )}
    </div>
  );
}
