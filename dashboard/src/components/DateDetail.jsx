import { useState, useEffect } from 'preact/compat';

function getItemId(tribunal, year) {
  return `djen-${tribunal.toLowerCase()}-${year}`;
}

function getZipUrl(itemId, date, tribunal) {
  const filename = `djen-${date}-${tribunal.toUpperCase()}.zip`;
  return `https://archive.org/download/${itemId}/${filename}`;
}

function formatSize(bytes) {
  const n = parseInt(bytes);
  if (isNaN(n)) return '';
  if (n > 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  if (n > 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${n} B`;
}

function shareUrl(dateStr, page, seq) {
  const base = window.location.pathname;
  let hash = dateStr;
  if (page) hash += `/${page}`;
  if (seq) hash += `/${seq}`;
  return `${window.location.origin}${base}#${hash}`;
}

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    return false;
  }
}

function ShareButton({ dateStr, page, seq, label }) {
  const [copied, setCopied] = useState(false);

  const handleClick = async (e) => {
    e.preventDefault();
    e.stopPropagation();
    const url = shareUrl(dateStr, page, seq);
    const ok = await copyToClipboard(url);
    if (ok) {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <button
      onClick={handleClick}
      className="text-[10px] text-gray-400 hover:text-accent transition-colors"
      title={copied ? 'Link copiado!' : `Copiar link: #${dateStr}${page ? '/' + page : ''}${seq ? '/' + seq : ''}`}
    >
      {copied ? 'Copiado!' : 'Compartilhar'}
    </button>
  );
}

async function cachedFetch(url) {
  if (typeof caches !== 'undefined') {
    const cache = await caches.open('causaganha-publications');
    const cached = await cache.match(url);
    if (cached) return cached;
    const res = await fetch(url, { redirect: 'follow' });
    if (res.ok) cache.put(url, res.clone());
    return res;
  }
  return fetch(url, { redirect: 'follow' });
}

export function DateDetail({ tribunalCode, dateStr, initialPage, initialSeq }) {
  const [totalPages, setTotalPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(initialPage || 1);
  const [publications, setPublications] = useState([]);
  const [zipSize, setZipSize] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState(null);
  const [highlightSeq, setHighlightSeq] = useState(initialSeq || null);

  const tribunal = tribunalCode.toUpperCase();
  const year = dateStr.substring(0, 4);
  const itemId = getItemId(tribunal, parseInt(year));
  const zipUrl = getZipUrl(itemId, dateStr, tribunal);

  function jsonName(pageNum) {
    return `${tribunal}-D-${dateStr}_${pageNum}.json`;
  }

  function jsonUrl(pageNum) {
    return `${zipUrl}/${jsonName(pageNum)}`;
  }

  async function loadPage(pageNum) {
    const url = jsonUrl(pageNum);
    const res = await cachedFetch(url);
    if (!res.ok) return null;
    const data = await res.json();
    return Array.isArray(data) ? data : (data.items || []);
  }

  // Update hash when navigating pages
  function updateHash(page) {
    const hash = page > 1 ? `${dateStr}/${page}` : dateStr;
    history.replaceState(null, '', `#${hash}`);
  }

  // Initial load
  useEffect(() => {
    async function init() {
      setLoading(true);
      setError(null);
      try {
        // Get ZIP size
        const metaRes = await fetch(`https://archive.org/metadata/${itemId}`);
        if (metaRes.ok) {
          const meta = await metaRes.json();
          const zipFilename = `djen-${dateStr}-${tribunal}.zip`;
          const zipFile = (meta.files || []).find(f => f.name === zipFilename);
          if (zipFile?.size) setZipSize(parseInt(zipFile.size));
        }

        // Probe pages
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

        // Load initial page(s) up to the requested page
        const targetPage = initialPage || 1;
        const allPubs = [];
        for (let p = 1; p <= Math.min(targetPage, validPages.length); p++) {
          const pubs = await loadPage(p);
          if (pubs) allPubs.push(...pubs);
        }
        setPublications(allPubs);
        setCurrentPage(Math.min(targetPage, validPages.length) || 1);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    init();
  }, [itemId, dateStr, tribunal]);

  // Scroll to highlighted publication
  useEffect(() => {
    if (highlightSeq && !loading) {
      const el = document.getElementById(`pub-${highlightSeq}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.add('ring-2', 'ring-accent');
        setTimeout(() => el.classList.remove('ring-2', 'ring-accent'), 3000);
      }
    }
  }, [highlightSeq, loading]);

  const handleLoadMore = async () => {
    const nextPage = currentPage + 1;
    if (nextPage > totalPages) return;
    setLoadingMore(true);
    try {
      const pubs = await loadPage(nextPage);
      if (pubs) {
        setPublications(prev => [...prev, ...pubs]);
        setCurrentPage(nextPage);
        updateHash(nextPage);
      }
    } catch {
      // ignore
    } finally {
      setLoadingMore(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Date header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-bold text-black dark:text-white font-mono">{dateStr}</h3>
          {zipSize && (
            <span className="text-xs text-gray-400">{formatSize(zipSize)}</span>
          )}
          {totalPages > 0 && (
            <span className="text-xs text-gray-400">{totalPages} pag.</span>
          )}
          <ShareButton dateStr={dateStr} />
        </div>
        <div className="flex gap-2">
          <a
            href={zipUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="px-2 py-1 text-[10px] bg-gray-100 dark:bg-slate-800 text-gray-500 rounded hover:text-black dark:hover:text-white transition-colors"
          >
            ZIP
          </a>
          <a
            href={`https://archive.org/details/${itemId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="px-2 py-1 text-[10px] bg-gray-100 dark:bg-slate-800 text-gray-500 rounded hover:text-black dark:hover:text-white transition-colors"
          >
            IA
          </a>
        </div>
      </div>

      {/* Loading */}
      {loading && (
        <div className="card p-8 text-center text-gray-500">Carregando publicacoes...</div>
      )}

      {/* Error */}
      {error && (
        <div className="card p-6 text-red-500 text-sm">Erro: {error}</div>
      )}

      {/* Publications */}
      {publications.length > 0 && (
        <div className="space-y-2">
          {publications.map((pub, i) => {
            const seq = i + 1;
            const pageNum = Math.floor(i / 1000) + 1;
            return (
              <div key={pub.id || i} id={`pub-${seq}`} className="card p-4 transition-all duration-300">
                <div className="flex items-start justify-between gap-2 mb-1">
                  <div className="flex-1 min-w-0 flex items-center gap-2">
                    <span className="text-[9px] text-gray-300 dark:text-gray-600 font-mono">{seq}</span>
                    {pub.numero_processo && (
                      <span className="font-mono text-sm text-accent font-medium">{pub.numero_processo}</span>
                    )}
                    {pub.tipoComunicacao && (
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-gray-100 dark:bg-slate-800 text-gray-500">
                        {pub.tipoComunicacao}
                      </span>
                    )}
                  </div>
                  <ShareButton dateStr={dateStr} page={pageNum} seq={seq} />
                </div>
                {pub.nomeOrgao && (
                  <div className="text-xs text-gray-500 dark:text-gray-400 mb-2">{pub.nomeOrgao}</div>
                )}
                {pub.texto && (
                  <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                    {pub.texto.length > 500 ? pub.texto.substring(0, 500) + '...' : pub.texto}
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
            );
          })}
        </div>
      )}

      {/* Load more */}
      {currentPage < totalPages && !loading && (
        <div className="text-center py-4">
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
          {publications.length.toLocaleString()} publicacoes
        </div>
      )}

      {/* No publications */}
      {!loading && publications.length === 0 && !error && (
        <div className="card p-8 text-center text-gray-500">
          Nenhuma publicacao encontrada.
        </div>
      )}
    </div>
  );
}
