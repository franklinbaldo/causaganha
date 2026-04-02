import { useState, useEffect } from 'preact/compat';

function getItemId(tribunal, year) {
  return `djen-${tribunal.toLowerCase()}-${year}`;
}

function getZipFilename(date, tribunal) {
  return `djen-${date}-${tribunal.toUpperCase()}.zip`;
}

function getDownloadUrl(itemId, filename) {
  return `https://archive.org/download/${itemId}/${filename}`;
}

export function ZipDetail({ tribunalCode, dateStr }) {
  const [zipInfo, setZipInfo] = useState(null);
  const [jsonFiles, setJsonFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedJson, setExpandedJson] = useState(null);
  const [publications, setPublications] = useState(null);
  const [loadingPubs, setLoadingPubs] = useState(false);

  const tribunal = tribunalCode.toUpperCase();
  const year = dateStr.substring(0, 4);
  const itemId = getItemId(tribunal, parseInt(year));
  const zipFilename = getZipFilename(dateStr, tribunal);
  const zipUrl = getDownloadUrl(itemId, zipFilename);

  const BASE = typeof import.meta !== 'undefined' ? (import.meta.env?.BASE_URL || '/causaganha/') : '/causaganha/';
  const baseUrl = BASE.endsWith('/') ? BASE : BASE + '/';

  useEffect(() => {
    async function fetchZipContents() {
      setLoading(true);
      setError(null);
      try {
        // Fetch item metadata to get file info
        const metaUrl = `https://archive.org/metadata/${itemId}`;
        const res = await fetch(metaUrl);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        // Find the ZIP file info
        const files = data.files || [];
        const zip = files.find(f => f.name === zipFilename);
        setZipInfo(zip || { name: zipFilename, size: '?' });

        // Try listing ZIP contents via IA's directory listing
        // IA serves directory listing when you request a ZIP path with trailing slash
        // We'll construct expected JSON filenames from the pattern
        // Pattern: {TRIBUNAL}-D-{date}_1.json, _2.json, etc
        // We don't know how many, so we'll probe or use a different approach

        // Probe for JSON files inside the ZIP.
        // Convention: {TRIBUNAL}-D-{date}_N.json where N starts at 1.
        // Probe in batch: try 1-10 in parallel, keep those that return 200.
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
        setJsonFiles(probes.filter(Boolean));
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    }
    fetchZipContents();
  }, [itemId, zipFilename, zipUrl, tribunal, dateStr]);

  const handleJsonClick = async (jsonName) => {
    if (expandedJson === jsonName) {
      setExpandedJson(null);
      setPublications(null);
      return;
    }

    setExpandedJson(jsonName);
    setLoadingPubs(true);
    setPublications(null);

    try {
      const jsonUrl = `${zipUrl}/${jsonName}`;
      const res = await fetch(jsonUrl, { redirect: 'follow' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();

      // Handle both formats: array or {items: [...]}
      const items = Array.isArray(data) ? data : (data.items || [data]);
      setPublications(items);
    } catch (err) {
      console.error('Failed to fetch JSON:', err);
      setPublications([]);
    } finally {
      setLoadingPubs(false);
    }
  };

  const formatSize = (bytes) => {
    const n = parseInt(bytes);
    if (isNaN(n)) return bytes;
    if (n > 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
    if (n > 1024) return `${(n / 1024).toFixed(0)} KB`;
    return `${n} B`;
  };

  return (
    <div className="flex flex-col gap-6">
      {/* Back nav */}
      <div className="flex items-center gap-4">
        <a
          href={`${baseUrl}monitor/${tribunal.toLowerCase()}`}
          className="flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-black dark:text-gray-400 dark:hover:text-white transition-colors"
        >
          <svg className="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          {tribunal}
        </a>
        <span className="text-gray-400">/</span>
        <span className="font-mono text-black dark:text-white">{dateStr}</span>
      </div>

      {/* ZIP info card */}
      <div className="card p-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-xl font-bold text-black dark:text-white">{tribunal} — {dateStr}</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 font-mono mt-1">{zipFilename}</p>
            {zipInfo?.size && zipInfo.size !== '?' && (
              <p className="text-xs text-gray-400 mt-1">{formatSize(zipInfo.size)}</p>
            )}
          </div>
          <a
            href={zipUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent-light transition-colors text-sm font-medium"
          >
            <svg className="w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Download ZIP
          </a>
        </div>

        <div className="text-xs text-gray-400 mb-2">
          Item: <a href={`https://archive.org/details/${itemId}`} target="_blank" rel="noopener noreferrer" className="text-accent hover:underline">{itemId}</a>
        </div>

        {loading && (
          <div className="text-sm text-gray-500 py-4">Carregando conteudo do ZIP...</div>
        )}

        {error && (
          <div className="text-sm text-red-500 py-4">Erro: {error}</div>
        )}

        {/* JSON files list */}
        {!loading && jsonFiles.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-black dark:text-white mb-3">
              Arquivos JSON ({jsonFiles.length})
            </h3>
            <div className="space-y-2">
              {jsonFiles.map(jsonName => (
                <div key={jsonName} className="border border-gray-200 dark:border-slate-800 rounded-lg overflow-hidden">
                  <button
                    onClick={() => handleJsonClick(jsonName)}
                    className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors"
                  >
                    <span className="font-mono text-sm text-black dark:text-white">{jsonName}</span>
                    <span className="text-xs text-gray-400">
                      {expandedJson === jsonName ? 'Fechar' : 'Ver publicacoes'}
                    </span>
                  </button>

                  {expandedJson === jsonName && (
                    <div className="border-t border-gray-200 dark:border-slate-800 p-4">
                      {loadingPubs && (
                        <div className="text-sm text-gray-500">Carregando publicacoes...</div>
                      )}
                      {publications && publications.length === 0 && (
                        <div className="text-sm text-gray-500">Nenhuma publicacao encontrada ou arquivo nao acessivel.</div>
                      )}
                      {publications && publications.length > 0 && (
                        <div className="space-y-3">
                          <div className="text-xs text-gray-400 mb-2">
                            {publications.length} publicacoes
                          </div>
                          {publications.slice(0, 50).map((pub, i) => (
                            <div key={pub.id || i} className="border-b border-gray-100 dark:border-slate-800 pb-3 last:border-0">
                              <div className="flex items-start justify-between gap-2">
                                <div className="flex-1 min-w-0">
                                  {pub.numero_processo && (
                                    <span className="font-mono text-xs text-accent">{pub.numero_processo}</span>
                                  )}
                                  {pub.nomeOrgao && (
                                    <span className="text-xs text-gray-500 ml-2">{pub.nomeOrgao}</span>
                                  )}
                                </div>
                                {pub.tipoComunicacao && (
                                  <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-gray-100 dark:bg-slate-800 text-gray-600 dark:text-gray-400">
                                    {pub.tipoComunicacao}
                                  </span>
                                )}
                              </div>
                              {pub.texto && (
                                <p className="text-xs text-gray-600 dark:text-gray-400 mt-1 line-clamp-3">
                                  {pub.texto.substring(0, 300)}{pub.texto.length > 300 ? '...' : ''}
                                </p>
                              )}
                              {pub.destinatarios?.length > 0 && (
                                <div className="flex flex-wrap gap-1 mt-1">
                                  {pub.destinatarios.slice(0, 3).map((d, j) => (
                                    <span key={j} className="text-[10px] bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 px-1.5 py-0.5 rounded">
                                      {d.nome}
                                    </span>
                                  ))}
                                  {pub.destinatarios.length > 3 && (
                                    <span className="text-[10px] text-gray-400">+{pub.destinatarios.length - 3}</span>
                                  )}
                                </div>
                              )}
                            </div>
                          ))}
                          {publications.length > 50 && (
                            <div className="text-xs text-gray-400 text-center pt-2">
                              Mostrando 50 de {publications.length} publicacoes
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {!loading && jsonFiles.length === 0 && !error && (
          <div className="text-sm text-gray-500 py-4">
            Nenhum arquivo JSON encontrado. O ZIP pode estar sendo processado pelo Internet Archive.
          </div>
        )}
      </div>
    </div>
  );
}
