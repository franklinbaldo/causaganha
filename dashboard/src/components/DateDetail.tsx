import { useState, useEffect, useCallback } from 'preact/compat';
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
  if (n> 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  if (n> 1024) return `${(n / 1024).toFixed(0)} KB`;
  return `${n} B`;
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 60) return `${diffMins}min atras`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h atras`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 30) return `${diffDays}d atras`;
  return date.toLocaleDateString('pt-BR');
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
    <button onClick={handleClick}>
      <svg  xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
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
  const [zipAddedDate, setZipAddedDate] = useState<string | null>(null);
  const [zipMd5, setZipMd5] = useState<string | null>(null);
  const [itemFileCount, setItemFileCount] = useState<number | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingMore, setLoadingMore] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [featuredPub, setFeaturedPub] = useState<FeaturedPub | null>(null);

  const tribunal = tribunalCode.toUpperCase();
  const year = dateStr.substring(0, 4);
  const itemId = getItemId(tribunal, parseInt(year));
  const zipUrl = getZipUrl(itemId, dateStr, tribunal);

  const jsonUrl = useCallback((pageNum: number): string => {
    return `${zipUrl}/${tribunal}-D-${dateStr}_${pageNum}.json`;
  }, [zipUrl, tribunal, dateStr]);

  const loadPage = useCallback(async (pageNum: number): Promise<Publication[] | null> => {
    const res = await cachedFetch(jsonUrl(pageNum));
    if (!res.ok) return null;
    const data = await res.json();
    return Array.isArray(data) ? data : (data.items || []);
  }, [jsonUrl]);

  useEffect(() => {
    async function init() {
      setLoading(true);
      setError(null);
      setFeaturedPub(null);
      try {
        // ZIP metadata from IA
        const metaRes = await fetch(`https://archive.org/metadata/${itemId}`);
        if (metaRes.ok) {
          const meta = await metaRes.json();
          const files = meta.files || [];
          const zipName = `djen-${dateStr}-${tribunal}.zip`;
          const zf = files.find((f: any) => f.name === zipName);
          if (zf?.size) setZipSize(parseInt(zf.size));
          if (zf?.mtime || zf?.addeddate) {
            const ts = zf.addeddate || new Date(parseInt(zf.mtime) * 1000).toISOString();
            setZipAddedDate(ts);
          }
          if (zf?.md5) setZipMd5(zf.md5);
          // Count non-system data files in the item
          const dataFiles = files.filter((f: any) => !f.name.startsWith('__') && !f.name.endsWith('.xml') && !f.name.endsWith('.sqlite') && f.source !== 'metadata');
          setItemFileCount(dataFiles.length);
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
            if (idx>= 0 && idx < pubs.length) {
              setFeaturedPub({ pub: pubs[idx], seq: initialSeq, page: targetPage });
            }
            setPublications(pubs);
            setCurrentPage(targetPage);
          }
        } else if (valid.length> 0) {
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
  }, [itemId, dateStr, tribunal, initialPage, initialSeq, jsonUrl, loadPage]);

  const handleLoadMore = async () => {
    const next = currentPage + 1;
    if (next> totalPages) return;
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
    <div>
      {/* Featured publication (deep-link) */}
      {featuredPub && (
        <div>
          <PublicationCard
            pub={featuredPub.pub} seq={featuredPub.seq}
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
                if (idx>= 0 && idx < pubs.length) {
                  setFeaturedPub({ pub: pubs[idx], seq: newSeq, page: newPage });
                }
              })();
            }}
          />
          <button
           onClick={() => { setFeaturedPub(null); history.replaceState(null, '', `#${dateStr}`); }}>
            Ver todas as publicacoes
          </button>
        </div>
      )}

      {/* Date header */}
      <div>
        <div>
          <h3>{dateStr}</h3>
          {zipSize != null && <span>{formatSize(zipSize)}</span>}
          {totalPages> 0 && <span>{totalPages} pag.</span>}
          {zipAddedDate && (
            <span  title={`Arquivado em ${new Date(zipAddedDate).toLocaleString('pt-BR')}`}>
              Arquivado {formatRelativeTime(zipAddedDate)}
            </span>
          )}
          {zipMd5 && (
            <span  title={`MD5: ${zipMd5}`}>
              MD5: {zipMd5.substring(0, 8)}...
            </span>
          )}
          <DateShareButton dateStr={dateStr} />
        </div>
        <div>
          <a href={zipUrl} target="_blank" rel="noopener noreferrer">ZIP</a>
          <a href={`https://archive.org/details/${itemId}`} target="_blank" rel="noopener noreferrer">IA</a>
          {itemFileCount != null && (
            <span>{itemFileCount} arquivos</span>
          )}
        </div>
      </div>

      {loading && <article>Carregando publicacoes...</article>}
      {error && <article>Erro: {error}</article>}

      {/* Publications list */}
      {publications.length> 0 && !featuredPub && (
        <div>
          {publications.map((pub, i) => (
            <PublicationCard
              key={pub.id || i} pub={pub}
              seq={i + 1}
              dateStr={dateStr}
              page={Math.floor(i / PUBS_PER_PAGE) + 1}
              compact
            />
          ))}
        </div>
      )}

      {currentPage < totalPages && !loading && (
        <div>
          <button onClick={handleLoadMore} disabled={loadingMore}>
            {loadingMore ? 'Carregando...' : `Pagina ${currentPage + 1} de ${totalPages}`}
          </button>
        </div>
      )}

      {currentPage>= totalPages && publications.length> 0 && !loading && !featuredPub && (
        <div>{publications.length.toLocaleString()} publicacoes</div>
      )}

      {!loading && publications.length === 0 && !error && (
        <article>Nenhuma publicacao encontrada.</article>
      )}
    </div>
  );
}
