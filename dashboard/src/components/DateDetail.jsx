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
  const [totalPages, setTotalPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [publications, setPublications] = useState([]);
  const [zipSize, setZipSize] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);

  const tribunal = tribunalCode.toUpperCase();
  const year = dateStr.substring(0, 4);
  const itemId = getItemId(tribunal, parseInt(year));
  const zipFilename = getZipFilename(dateStr, tribunal);
  const zipUrl = getZipUrl(itemId, zipFilename);

  const BASE = typeof import.meta !== 'undefined' ? (import.meta.env?.BASE_URL || '/causaganha/') : '/causaganha/';
  const baseUrl = BASE.endsWith('/') ? BASE : BASE + '/';

  function jsonName(pageNum) {
    return `${tribunal}-D-${dateStr}_${pageNum}.json`;
  }

  function jsonUrl(pageNum) {
    return `${zipUrl}/${jsonName(pageNum)}`;
  }

  async function loadPage(pageNum) {
    const url = jsonUrl(pageNum);
    const res = await fetch(url, { redirect: 'follow' });
    if (!res.ok) return null;
    const data = await res.json();
    return Array.isArray(data) ? data : (data.items || []);
  }

  // Initial load: discover page count + load first page
  useEffect(() => {
    async function init() {
      setLoading(true);
      setError(null);
      try {
        // Get ZIP size
        const metaRes = await fetch(`https://archive.org/metadata/${itemId}`);
        if (metaRes.ok) {
          const meta = await metaRes.json();
          const zipFile = (meta.files || []).find(f => f.name === zipFilename);
          if (zipFile?.size) setZipSize(parseInt(zipFile.size));
        }

        // Probe how many pages exist (parallel HEAD requests)
        const candidates = Array.from({ length: 30 }, (_, i) => i + 1);
        const probes = await Promise.all(
          candidates.map(async (n) => {
            try {
              const res = await fetch(jsonUrl(n), { method: 'HEAD', redirect: 'follow' });
              return res.ok ? n : null;
            } catch {
              return null;
            }
          })
        );
        const validPages = probes.filter(Boolean);
        setTotalPages(validPages.length);

        // Load first page immediately
        if (validPages.length > 0) {
          const pubs = await loadPage(1);
          if (pubs) setPublications(pubs);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    init();
  }, [itemId, zipFilename, zipUrl, tribunal, dateStr]);

  const handleLoadMore = async () => {
    const nextPage = currentPage + 1;
    if (nextPage > totalPages) return;
    setLoadingMore(true);
    try {
      const pubs = await loadPage(nextPage);
      if (pubs) {
        setPublications(prev => [...prev, ...pubs]);
        setCurrentPage(nextPage);
      }
    } catch {
      // ignore
    } finally {
      setLoadingMore(false);
    }
  };

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
            <div className="flex gap-3 mt-1 text-sm text-gray-500">
              {zipSize && <span>{formatSize(zipSize)}</span>}
              {totalPages > 0 && <span>{totalPages} paginas</span>}
              {publications.length > 0 && <span>{publications.length.toLocaleString()} publicacoes carregadas</span>}
            </div>
          </div>
          <div className="flex gap-2">
            <a
              href={zipUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 bg-gray-100 dark:bg-slate-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-700 transition-colors text-xs"
            >
              ZIP
            </a>
            <a
              href={`https://archive.org/details/${itemId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-3 py-1.5 bg-gray-100 dark:bg-slate-800 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-700 transition-colors text-xs"
            >
              IA
            </a>
          </div>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="card p-8 text-center text-gray-500">
          Carregando publicacoes...
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="card p-6 text-red-500 text-sm">Erro: {error}</div>
      )}

      {/* Publications list */}
      {publications.length > 0 && (
        <div className="space-y-2">
          {publications.map((pub, i) => (
            <div key={pub.id || i} className="card p-4">
              <div className="flex items-start justify-between gap-2 mb-2">
                <div className="flex-1 min-w-0">
                  {pub.numero_processo && (
                    <span className="font-mono text-sm text-accent font-medium">{pub.numero_processo}</span>
                  )}
                  {pub.tipoComunicacao && (
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-gray-100 dark:bg-slate-800 text-gray-500 ml-2">
                      {pub.tipoComunicacao}
                    </span>
                  )}
                </div>
              </div>
              {pub.nomeOrgao && (
                <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">{pub.nomeOrgao}</div>
              )}
              {pub.texto && (
                <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                  {pub.texto.length > 500
                    ? pub.texto.substring(0, 500) + '...'
                    : pub.texto}
                </p>
              )}
              {pub.destinatarios?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {pub.destinatarios.map((d, j) => (
                    <span key={j} className="text-[10px] bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 px-1.5 py-0.5 rounded">
                      {d.nome}
                    </span>
                  ))}
                </div>
              )}
              {pub.destinatarioadvogados?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1">
                  {pub.destinatarioadvogados.map((da, j) => (
                    <span key={j} className="text-[10px] bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300 px-1.5 py-0.5 rounded">
                      {da.advogado?.nome} {da.advogado?.numero_oab && `(OAB ${da.advogado.uf_oab} ${da.advogado.numero_oab})`}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Load more */}
      {currentPage < totalPages && !loading && (
        <div className="text-center">
          <button
            onClick={handleLoadMore}
            disabled={loadingMore}
            className="px-6 py-2 bg-accent text-white rounded-lg hover:bg-accent-light transition-colors text-sm font-medium disabled:opacity-50"
          >
            {loadingMore
              ? 'Carregando...'
              : `Carregar pagina ${currentPage + 1} de ${totalPages}`}
          </button>
        </div>
      )}

      {/* All loaded */}
      {currentPage >= totalPages && publications.length > 0 && !loading && (
        <div className="text-center text-xs text-gray-400 pb-4">
          Todas as {publications.length.toLocaleString()} publicacoes carregadas
        </div>
      )}

      {/* No publications */}
      {!loading && publications.length === 0 && !error && (
        <div className="card p-8 text-center text-gray-500">
          Nenhuma publicacao encontrada. O ZIP pode estar sendo processado pelo Internet Archive.
        </div>
      )}
    </div>
  );
}
