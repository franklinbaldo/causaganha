import { useState, useEffect } from 'preact/compat';

interface ParquetFile {
  name: string;
  size: number;
  url: string;
}

function formatSize(bytes: number): string {
  if (bytes> 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024 * 1024)).toFixed(1)} GB`;
  if (bytes> 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  if (bytes> 1024) return `${(bytes / 1024).toFixed(0)} KB`;
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
    if (snapshotParquetFiles && snapshotParquetFiles.length> 0) {
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
  }, [itemId, baseUrl, snapshotParquetFiles]);

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
       className="btn btn-secondary"
       style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
       onClick={() => setExpanded(true)}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} style={{ width: '1.25rem', height: '1.25rem' }}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 7v10c0 2 1 3 3 3h10c2 0 3-1 3-3V7c0-2-1-3-3-3H7C5 4 4 5 4 7z" />
          <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6M12 9v6" />
        </svg>
        Acesso aos dados (DuckDB / Parquet)
      </button>
    );
  }

  return (
    <div className="card bg-base-100 shadow-sm border border-base-300"><div className="card-body">
      <header>
        <h4>Acesso aos Dados</h4>
        <button
          className="btn btn-outline"
          onClick={() => setExpanded(false)}>
          Fechar
        </button>
      </header>

      {/* DuckDB catalog query */}
      <section>
        <div>
          <span>Consulta via Catalogo (DuckDB)</span>
          <button
            className="btn btn-outline"
            onClick={() => copyToClipboard(catalogQuery, 'catalog')}>
            {copied === 'catalog' ? 'Copiado!' : 'Copiar'}
          </button>
        </div>
        <pre>
          {catalogQuery}
        </pre>
      </section>

      {/* Parquet files */}
      {loading && <p aria-busy="true">Carregando arquivos...</p>}

      {parquetFiles.length> 0 && (
        <section>
          <strong>
            Arquivos Parquet ({parquetFiles.length})
          </strong>
          <div>
            {parquetFiles.map(f => (
              <div key={f.name}>
                <div>
                  <a
                    href={f.url} target="_blank"
                    rel="noopener noreferrer"
                    className="text-accent">
                    {f.name}
                  </a>
                  <small>{formatSize(f.size)}</small>
                </div>
                <div>
                  <code>
                    {duckdbQuery(f.name).substring(0, 80)}...
                  </code>
                  <button
                    className="btn btn-outline"
                    onClick={() => copyToClipboard(duckdbQuery(f.name), f.name)}>
                    {copied === f.name ? 'Copiado!' : 'SQL'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {!loading && parquetFiles.length === 0 && (
        <p>Nenhum arquivo Parquet encontrado neste item.</p>
      )}
    </div></div>
  );
}
