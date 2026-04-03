import { useState, useEffect } from 'preact/compat';
import { PublicationCard } from './PublicationCard';

const PUBS_PER_PAGE = 1000;

interface Publication {
  id?: string;
  numero_processo?: string;
  tipoComunicacao?: string;
  nomeOrgao?: string;
  texto?: string;
  destinatarios?: { nome: string }[];
  destinatarioadvogados?: { advogado?: { nome?: string; numero_oab?: string; uf_oab?: string } }[];
}

interface FeaturedPub {
  pub: Publication;
  seq: number;
  page: number;
}

function getItemId(tribunal: string, year: number): string {
  return `djen-${tribunal.toLowerCase()}-${year}`;
}

function getZipUrl(itemId: string, date: string, tribunal: string): string {
  return `https://archive.org/download/${itemId}/djen-${date}-${tribunal.toUpperCase()}.zip`;
}

function formatSize(bytes: string | number): string {
  const n = parseInt(String(bytes));
  if (isNaN(n)) return '';
  if (n > 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  if (n > 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${n} B`;
}

function DateShareButton({ dateStr }: { dateStr: string }) {
  const [copied, setCopied] = useState(false);
  const handleClick = (e: MouseEvent) => {
    e.preventDefault();
    const url = `${window.location.origin}${window.location.pathname}#${dateStr}`;
    navigator.clipboard?.writeText(url);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button onClick={handleClick} className="inline-flex items-center gap-1 text-xs text-gray-400 hover:text-accent transition-colors px-2 py-1 rounded hover:bg-gray-100 dark:hover:bg-slate-800">
      <svg className="w-3.5 h-3.5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
      </svg>
      {copied ? 'Copiado!' : 'Link'}
    </button>
  );
}

async function cachedFetch(url: string): Promise<Response> {
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

interface DateDetailProps {
  tribunalCode: string;
  dateStr: string;
  initialPage?: number;
  initialSeq?: number;
}

export function DateDetail({ tribunalCode, dateStr, initialPage, initialSeq }: DateDetailProps) {
  const [totalPages, setTotalPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(initialPage || 1);
  const [publications, setPublications] = useState<Publication[]>([]);
  const [zipSize, setZipSize] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [featuredPub, setFeaturedPub] = useState<FeaturedPub | null>(null);

  const tribunal = tribunalCode.toUpperCase();
  const year = dateStr.substring(0, 4);
  const itemId = getItemId(tribunal, parseInt(year));
  const zipUrl = getZipUrl(itemId, dateStr, tribunal);

  function jsonUrl(pageNum: number): string {
    return `${zipUrl}/${tribunal}-D-${dateStr}_${pageNum}.json`;
  }

  async function loadPage(pageNum: number): Promise<Publication[] | null> {
    const res = await cachedFetch(jsonUrl(pageNum));
    if (!res.ok) return null;
    const data = await res.json();
    return Array.isArray(data) ? data : (data.items || []);
  }

  useEffect(() => {
    async function init() {
      setLoading(true);
      setError(null);
      setFeaturedPub(null);
      try {
        // ZIP size
        const metaRes = await fetch(`https://archive.org/metadata/${itemId}`);
        if (metaRes.ok) {
          const meta = await metaRes.json();
          const zf = (meta.files || []).find((f: any) => f.name === `djen-${dateStr}-${tribunal}.zip`);
          if (zf?.size) setZipSize(parseInt(zf.size));
        }

        // Probe pages
        const probes = await Promise.all(
          Array.from({ length: 30 }, (_, i) => i + 1).map(async (n) => {
            try {
              const res = await fetch(jsonUrl(n), { method: 'HEAD', redirect: 'follow' });
              return res.ok ? n : null;
            } catch { return null; }
          })
        );
        const valid = probes.filter(Boolean) as number[];
        setTotalPages(valid.length);

        // Load target page
        const targetPage = initialPage || 1;
        if (initialSeq && targetPage <= valid.length) {
          // Deep-link to specific publication
          const pubs = await loadPage(targetPage);
          if (pubs) {
            const idx = initialSeq - ((targetPage - 1) * PUBS_PER_PAGE) - 1;
            if (idx >= 0 && idx < pubs.length) {
              setFeaturedPub({ pub: pubs[idx], seq: initialSeq, page: targetPage });
            }
            setPublications(pubs);
            setCurrentPage(targetPage);
          }
        } else if (valid.length > 0) {
          const pubs = await loadPage(1);
          if (pubs) setPublications(pubs);
          setCurrentPage(1);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    }
    init();
  }, [itemId, dateStr, tribunal]);

  const handleLoadMore = async () => {
    const next = currentPage + 1;
    if (next > totalPages) return;
    setLoadingMore(true);
    try {
      const pubs = await loadPage(next);
      if (pubs) {
        setPublications(prev => [...prev, ...pubs]);
        setCurrentPage(next);
        history.replaceState(null, '', `#${dateStr}/${next}`);
      }
    } finally {
      setLoadingMore(false);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      {/* Featured publication (deep-link) */}
      {featuredPub && (
        <div>
          <PublicationCard
            pub={featuredPub.pub}
            seq={featuredPub.seq}
            dateStr={dateStr}
            page={featuredPub.page}
            totalSeq={publications.length || totalPages * PUBS_PER_PAGE}
            onNavigate={(newSeq: number) => {
              if (newSeq < 1) return;
              const newPage = Math.ceil(newSeq / PUBS_PER_PAGE);
              const hash = `${dateStr}/${newPage}/${newSeq}`;
              history.replaceState(null, '', `#${hash}`);
              // Load the page if needed and update featured
              (async () => {
                let pubs = publications;
                if (newPage !== featuredPub.page || pubs.length === 0) {
                  const loaded = await loadPage(newPage);
                  if (loaded) {
                    pubs = loaded;
                    setPublications(loaded);
                    setCurrentPage(newPage);
                  }
                }
                const idx = newSeq - ((newPage - 1) * PUBS_PER_PAGE) - 1;
                if (idx >= 0 && idx < pubs.length) {
                  setFeaturedPub({ pub: pubs[idx], seq: newSeq, page: newPage });
                }
              })();
            }}
          />
          <button
            onClick={() => { setFeaturedPub(null); history.replaceState(null, '', `#${dateStr}`); }}
            className="mt-2 text-xs text-gray-400 hover:text-accent transition-colors"
          >
            Ver todas as publicacoes
          </button>
        </div>
      )}

      {/* Date header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-bold text-black dark:text-white font-mono">{dateStr}</h3>
          {zipSize && <span className="text-xs text-gray-400">{formatSize(zipSize)}</span>}
          {totalPages > 0 && <span className="text-xs text-gray-400">{totalPages} pag.</span>}
          <DateShareButton dateStr={dateStr} />
        </div>
        <div className="flex gap-2">
          <a href={zipUrl} target="_blank" rel="noopener noreferrer" className="px-2 py-1 text-[10px] bg-gray-100 dark:bg-slate-800 text-gray-500 rounded hover:text-black dark:hover:text-white transition-colors">ZIP</a>
          <a href={`https://archive.org/details/${itemId}`} target="_blank" rel="noopener noreferrer" className="px-2 py-1 text-[10px] bg-gray-100 dark:bg-slate-800 text-gray-500 rounded hover:text-black dark:hover:text-white transition-colors">IA</a>
        </div>
      </div>

      {loading && <div className="card p-8 text-center text-gray-500">Carregando publicacoes...</div>}
      {error && <div className="card p-6 text-red-500 text-sm">Erro: {error}</div>}

      {/* Publications list */}
      {publications.length > 0 && !featuredPub && (
        <div className="space-y-2">
          {publications.map((pub, i) => (
            <PublicationCard
              key={pub.id || i}
              pub={pub}
              seq={i + 1}
              dateStr={dateStr}
              page={Math.floor(i / PUBS_PER_PAGE) + 1}
              compact
            />
          ))}
        </div>
      )}

      {currentPage < totalPages && !loading && (
        <div className="text-center py-4">
          <button onClick={handleLoadMore} disabled={loadingMore} className="px-6 py-2 bg-accent text-white rounded-lg hover:bg-accent-light transition-colors text-sm font-medium disabled:opacity-50">
            {loadingMore ? 'Carregando...' : `Pagina ${currentPage + 1} de ${totalPages}`}
          </button>
        </div>
      )}

      {currentPage >= totalPages && publications.length > 0 && !loading && !featuredPub && (
        <div className="text-center text-xs text-gray-400 pb-4">{publications.length.toLocaleString()} publicacoes</div>
      )}

      {!loading && publications.length === 0 && !error && (
        <div className="card p-8 text-center text-gray-500">Nenhuma publicacao encontrada.</div>
      )}
    </div>
  );
}
