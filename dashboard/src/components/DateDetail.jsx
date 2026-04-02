import { useState, useEffect } from 'preact/compat';

function getItemId(tribunal, year) {
  return `djen-${tribunal.toLowerCase()}-${year}`;
}

function getZipFilename(date, tribunal) {
  return `djen-${date}-${tribunal.toUpperCase()}.zip`;
}

function getZipUrl(itemId, filename) {
  return `https://archive.org/download/${itemId}/${filename}`;
}

function formatSize(bytes) {
  const n = parseInt(bytes);
  if (isNaN(n)) return '';
  if (n > 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  if (n > 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${n} B`;
}

export function DateDetail({ tribunalCode, dateStr }) {
  const [pages, setPages] = useState([]);
  const [zipSize, setZipSize] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const tribunal = tribunalCode.toUpperCase();
  const year = dateStr.substring(0, 4);
  const itemId = getItemId(tribunal, parseInt(year));
  const zipFilename = getZipFilename(dateStr, tribunal);
  const zipUrl = getZipUrl(itemId, zipFilename);

  const BASE = typeof import.meta !== 'undefined' ? (import.meta.env?.BASE_URL || '/causaganha/') : '/causaganha/';
  const baseUrl = BASE.endsWith('/') ? BASE : BASE + '/';

  useEffect(() => {
    async function discover() {
      setLoading(true);
      setError(null);
      try {
        // Get ZIP size from item metadata
        const metaRes = await fetch(`https://archive.org/metadata/${itemId}`);
        if (metaRes.ok) {
          const meta = await metaRes.json();
          const zipFile = (meta.files || []).find(f => f.name === zipFilename);
          if (zipFile?.size) setZipSize(parseInt(zipFile.size));
        }

        // Probe for pages (JSON files inside ZIP)
        // Convention: {TRIBUNAL}-D-{date}_N.json
        const candidates = Array.from({ length: 20 }, (_, i) =>
          `${tribunal}-D-${dateStr}_${i + 1}.json`
        );
        const probes = await Promise.all(
          candidates.map(async (name) => {
            try {
              const res = await fetch(`${zipUrl}/${name}`, { method: 'HEAD', redirect: 'follow' });
              return res.ok ? name : null;
            } catch {
              return null;
            }
          })
        );
        setPages(probes.filter(Boolean));
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    discover();
  }, [itemId, zipFilename, zipUrl, tribunal, dateStr]);

  const totalPubs = pages.length * 1000; // ~1000 per page

  return (
    <div className="flex flex-col gap-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <a href={`${baseUrl}monitor`} className="text-gray-400 hover:text-black dark:hover:text-white transition-colors">Monitor</a>
        <span className="text-gray-300 dark:text-gray-600">/</span>
        <a href={`${baseUrl}monitor/${tribunal.toLowerCase()}`} className="text-gray-400 hover:text-black dark:hover:text-white transition-colors">{tribunal}</a>
        <span className="text-gray-300 dark:text-gray-600">/</span>
        <span className="font-mono text-black dark:text-white">{dateStr}</span>
      </div>

      {/* Header */}
      <div className="card p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold text-black dark:text-white">{tribunal} — {dateStr}</h2>
            {zipSize && (
              <p className="text-sm text-gray-500 mt-1">{formatSize(zipSize)}</p>
            )}
            {!loading && pages.length > 0 && (
              <p className="text-sm text-gray-400 mt-1">
                {pages.length} paginas (~{totalPubs.toLocaleString()} publicacoes)
              </p>
            )}
          </div>
          <div className="flex gap-2">
            <a
              href={zipUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-slate-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-700 transition-colors text-sm"
            >
              Download ZIP
            </a>
            <a
              href={`https://archive.org/details/${itemId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2 bg-gray-100 dark:bg-slate-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-700 transition-colors text-sm"
            >
              Internet Archive
            </a>
          </div>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="text-sm text-gray-500">Descobrindo paginas...</div>
      )}

      {/* Error */}
      {error && (
        <div className="text-sm text-red-500">Erro: {error}</div>
      )}

      {/* Pages grid */}
      {!loading && pages.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          {pages.map((name, i) => {
            const pageNum = i + 1;
            const jsonUrl = `${zipUrl}/${name}`;
            return (
              <a
                key={name}
                href={jsonUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="card p-4 flex flex-col items-center gap-2 hover:border-accent transition-all no-underline group"
              >
                <span className="text-2xl font-bold font-mono text-gray-300 dark:text-gray-600 group-hover:text-accent transition-colors">
                  {pageNum}
                </span>
                <span className="text-[10px] text-gray-500 dark:text-gray-400">
                  ~1000 pub.
                </span>
              </a>
            );
          })}
        </div>
      )}

      {/* No pages */}
      {!loading && pages.length === 0 && !error && (
        <div className="card p-6 text-center text-gray-500">
          Nenhuma pagina encontrada. O ZIP pode estar sendo processado pelo Internet Archive.
        </div>
      )}
    </div>
  );
}
