import { useState, useEffect } from 'preact/compat';

interface ParquetFile {
  name: string;
  size: number;
  url: string;
}

function formatSize(bytes: number): string {
  if (bytes > 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  if (bytes > 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  if (bytes > 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${bytes} B`;
}

interface DataAccessPanelProps {
  tribunalCode: string;
  year: number;
  /** Pre-fetched parquet files from IA snapshot (optional) */
  snapshotParquetFiles?: { name: string; size: number }[];
}

export function DataAccessPanel({ tribunalCode, year, snapshotParquetFiles }: DataAccessPanelProps) {
  const [parquetFiles, setParquetFiles] = useState<ParquetFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  const itemId = `djen-${tribunalCode.toLowerCase()}-${year}`;
  const baseUrl = `https://archive.org/download/${itemId}`;

  useEffect(() => {
    // Use snapshot data if available
    if (snapshotParquetFiles && snapshotParquetFiles.length > 0) {
      setParquetFiles(snapshotParquetFiles.map(f => ({
        ...f,
        url: `${baseUrl}/${f.name}`,
      })));
      return;
    }

    // Otherwise fetch from IA metadata API
    async function fetchFiles() {
      setLoading(true);
      try {
        const res = await fetch(`https://archive.org/metadata/${itemId}/files`);
        if (!res.ok) return;
        const data = await res.json();
        const files = (data?.result || data || [])
          .filter((f: any) => f.name?.endsWith('.parquet'))
          .map((f: any) => ({
            name: f.name,
            size: parseInt(f.size) || 0,
            url: `${baseUrl}/${f.name}`,
          }));
        setParquetFiles(files);
      } catch {
        // Silent fail
      } finally {
        setLoading(false);
      }
    }
    fetchFiles();
  }, [itemId]);

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard?.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(null), 2000);
  };

  const duckdbQuery = (fileName: string) =>
    `SELECT * FROM read_parquet('${baseUrl}/${fileName}') LIMIT 100;`;

  const catalogQuery = `-- Query all ${tribunalCode} data via the CausaGanha catalog
ATTACH 'https://archive.org/download/causaganha-catalog/catalog.duckdb' AS cg (READ_ONLY);
SELECT * FROM cg.comunicacoes WHERE tribunal = '${tribunalCode}' LIMIT 100;`;

  if (!expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className="flex items-center gap-2 text-xs text-gray-500 hover:text-accent dark:text-gray-400 dark:hover:text-accent transition-colors"
      >
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2 1 3 3 3h10c2 0 3-1 3-3V7c0-2-1-3-3-3H7C5 4 4 5 4 7z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6M12 9v6" />
        </svg>
        Acesso aos dados (DuckDB / Parquet)
      </button>
    );
  }

  return (
    <div className="bg-gray-50 dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-black dark:text-white">Acesso aos Dados</h4>
        <button
          onClick={() => setExpanded(false)}
          className="text-xs text-gray-400 hover:text-black dark:hover:text-white"
        >
          Fechar
        </button>
      </div>

      {/* DuckDB catalog query */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs font-medium text-gray-600 dark:text-gray-300">Consulta via Catalogo (DuckDB)</span>
          <button
            onClick={() => copyToClipboard(catalogQuery, 'catalog')}
            className="text-[10px] text-accent hover:underline"
          >
            {copied === 'catalog' ? 'Copiado!' : 'Copiar'}
          </button>
        </div>
        <pre className="bg-white dark:bg-slate-900 rounded p-2 text-[11px] font-mono text-gray-700 dark:text-gray-300 overflow-x-auto whitespace-pre-wrap">
          {catalogQuery}
        </pre>
      </div>

      {/* Parquet files */}
      {loading && <div className="text-xs text-gray-500">Carregando arquivos...</div>}

      {parquetFiles.length > 0 && (
        <div>
          <span className="text-xs font-medium text-gray-600 dark:text-gray-300 block mb-2">
            Arquivos Parquet ({parquetFiles.length})
          </span>
          <div className="space-y-2">
            {parquetFiles.map(f => (
              <div key={f.name} className="bg-white dark:bg-slate-900 rounded p-2">
                <div className="flex items-center justify-between mb-1">
                  <a
                    href={f.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-mono text-accent hover:underline truncate"
                  >
                    {f.name}
                  </a>
                  <span className="text-[10px] text-gray-400 ml-2 flex-shrink-0">{formatSize(f.size)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <code className="text-[10px] font-mono text-gray-500 truncate">
                    {duckdbQuery(f.name).substring(0, 80)}...
                  </code>
                  <button
                    onClick={() => copyToClipboard(duckdbQuery(f.name), f.name)}
                    className="text-[10px] text-accent hover:underline ml-2 flex-shrink-0"
                  >
                    {copied === f.name ? 'Copiado!' : 'SQL'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!loading && parquetFiles.length === 0 && (
        <div className="text-xs text-gray-500">Nenhum arquivo Parquet encontrado neste item.</div>
      )}
    </div>
  );
}
