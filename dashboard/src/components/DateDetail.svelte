<script lang="ts">
  import { onMount } from 'svelte';
  import PublicationCard from './PublicationCard.svelte';

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

  function formatRelativeTime(dateStr: string): string {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 60) return `${diffMins} min atrás`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h atrás`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 30) return `${diffDays}d atrás`;
    return date.toLocaleDateString('pt-BR');
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

  let { tribunalCode, dateStr, initialPage, initialSeq }: DateDetailProps = $props();

  let totalPages = $state<number>(0);
  let currentPage = $state<number>(initialPage || 1);
  let publications = $state<Publication[]>([]);
  let zipSize = $state<number | null>(null);
  let zipAddedDate = $state<string | null>(null);
  let zipMd5 = $state<string | null>(null);
  let itemFileCount = $state<number | null>(null);
  let loading = $state<boolean>(true);
  let loadingMore = $state<boolean>(false);
  let error = $state<string | null>(null);
  let featuredPub = $state<FeaturedPub | null>(null);

  let tribunal = $derived(tribunalCode.toUpperCase());
  let year = $derived(dateStr.substring(0, 4));
  let itemId = $derived(getItemId(tribunal, parseInt(year)));
  let zipUrl = $derived(getZipUrl(itemId, dateStr, tribunal));

  function jsonUrl(pageNum: number): string {
    return `${zipUrl}/${tribunal}-D-${dateStr}_${pageNum}.json`;
  }

  async function loadPage(pageNum: number): Promise<Publication[] | null> {
    const res = await cachedFetch(jsonUrl(pageNum));
    if (!res.ok) return null;
    const data = await res.json();
    return Array.isArray(data) ? data : (data.items || []);
  }

  $effect(() => {
    // Track reactive deps
    const _itemId = itemId;
    const _dateStr = dateStr;
    const _tribunal = tribunal;
    const _initialPage = initialPage;
    const _initialSeq = initialSeq;

    async function init() {
      loading = true;
      error = null;
      featuredPub = null;
      try {
        // ZIP metadata from IA
        const metaRes = await fetch(`https://archive.org/metadata/${_itemId}`);
        if (metaRes.ok) {
          const meta = await metaRes.json();
          const files = meta.files || [];
          const zipName = `djen-${_dateStr}-${_tribunal}.zip`;
          const zf = files.find((f: any) => f.name === zipName);
          if (zf?.size) zipSize = parseInt(zf.size);
          if (zf?.mtime || zf?.addeddate) {
            const ts = zf.addeddate || new Date(parseInt(zf.mtime) * 1000).toISOString();
            zipAddedDate = ts;
          }
          if (zf?.md5) zipMd5 = zf.md5;
          // Count non-system data files in the item
          const dataFiles = files.filter((f: any) => !f.name.startsWith('__') && !f.name.endsWith('.xml') && !f.name.endsWith('.sqlite') && f.source !== 'metadata');
          itemFileCount = dataFiles.length;
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
        totalPages = valid.length;

        // Load target page
        const targetPage = _initialPage || 1;
        if (_initialSeq && targetPage <= valid.length) {
          // Deep-link to specific publication
          const pubs = await loadPage(targetPage);
          if (pubs) {
            const idx = _initialSeq - ((targetPage - 1) * PUBS_PER_PAGE) - 1;
            if (idx >= 0 && idx < pubs.length) {
              featuredPub = { pub: pubs[idx], seq: _initialSeq, page: targetPage };
            }
            publications = pubs;
            currentPage = targetPage;
          }
        } else if (valid.length > 0) {
          const pubs = await loadPage(1);
          if (pubs) publications = pubs;
          currentPage = 1;
        }
      } catch (err: unknown) {
        error = err instanceof Error ? err.message : String(err);
      } finally {
        loading = false;
      }
    }
    init();
  });

  async function handleLoadMore() {
    const next = currentPage + 1;
    if (next > totalPages) return;
    loadingMore = true;
    try {
      const pubs = await loadPage(next);
      if (pubs) {
        publications = [...publications, ...pubs];
        currentPage = next;
        history.replaceState(null, '', `#${dateStr}/${next}`);
      }
    } finally {
      loadingMore = false;
    }
  }

  function handleNavigate(newSeq: number) {
    if (newSeq < 1) return;
    const newPage = Math.ceil(newSeq / PUBS_PER_PAGE);
    const hash = `${dateStr}/${newPage}/${newSeq}`;
    history.replaceState(null, '', `#${hash}`);
    (async () => {
      let pubs = publications;
      if (newPage !== featuredPub?.page || pubs.length === 0) {
        const loaded = await loadPage(newPage);
        if (loaded) {
          pubs = loaded;
          publications = loaded;
          currentPage = newPage;
        }
      }
      const idx = newSeq - ((newPage - 1) * PUBS_PER_PAGE) - 1;
      if (idx >= 0 && idx < pubs.length) {
        featuredPub = { pub: pubs[idx], seq: newSeq, page: newPage };
      }
    })();
  }

  let shareLinkCopied = $state(false);

  function handleShareClick(e: MouseEvent) {
    e.preventDefault();
    const url = `${window.location.origin}${window.location.pathname}#${dateStr}`;
    navigator.clipboard?.writeText(url);
    shareLinkCopied = true;
    setTimeout(() => shareLinkCopied = false, 2000);
  }

  function handleDismissFeatured() {
    featuredPub = null;
    history.replaceState(null, '', `#${dateStr}`);
  }
</script>

{#snippet DateShareButton()}
  <button
    onclick={handleShareClick}
    class="btn-outline-secondary"
  >
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
      <path stroke-linecap="round" stroke-linejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
    </svg>
    {shareLinkCopied ? 'Copiado!' : 'Link'}
  </button>
{/snippet}

<div>
  {#if featuredPub}
    <div>
      <PublicationCard
        pub={featuredPub.pub}
        seq={featuredPub.seq}
        dateStr={dateStr}
        page={featuredPub.page}
        totalSeq={publications.length || totalPages * PUBS_PER_PAGE}
        onNavigate={handleNavigate}
      />
      <button
        class="btn"
        onclick={handleDismissFeatured}
      >
        Ver todas as publicações
      </button>
    </div>
  {/if}

  <!-- Date header -->
  <div class="card">
    <div class="card-body">
      <header class="header-row">
        <div class="header-info">
          <h3 class="date-title">{dateStr}</h3>
          {#if zipSize != null}
            <span class="badge-accent">{formatSize(zipSize)}</span>
          {/if}
          {#if totalPages > 0}
            <span class="meta-dim">{totalPages} pág.</span>
          {/if}
          {#if itemFileCount != null}
            <span class="meta-dim">{itemFileCount} arquivos</span>
          {/if}
        </div>
        <div class="header-actions" aria-label="Ações do arquivo">
          {@render DateShareButton()}
          <a href={zipUrl} class="btn-outline-secondary" target="_blank" rel="noopener noreferrer">Baixar ZIP</a>
          <a href={`https://archive.org/details/${itemId}`} class="btn-outline-secondary" target="_blank" rel="noopener noreferrer">Ver no IA</a>
        </div>
      </header>
      <div class="meta-row">
        {#if zipAddedDate}
          <span title={`Arquivado em ${new Date(zipAddedDate).toLocaleString('pt-BR')}`}>
            Arquivado {formatRelativeTime(zipAddedDate)}
          </span>
        {/if}
        {#if zipMd5}
          <span title={`MD5: ${zipMd5}`}>
            MD5: {zipMd5.substring(0, 8)}...
          </span>
        {/if}
      </div>
    </div>
  </div>

  {#if loading}
    <div class="loading-center"><span class="spinner spinner--lg"></span></div>
  {/if}

  {#if error}
    <div class="card"><div class="card-body error-text">Erro: {error}</div></div>
  {/if}

  {#if publications.length > 0 && !featuredPub}
    <div>
      {#each publications as pub, i (pub.id || i)}
        <PublicationCard
          pub={pub}
          seq={i + 1}
          dateStr={dateStr}
          page={Math.floor(i / PUBS_PER_PAGE) + 1}
          compact
        />
      {/each}
    </div>
  {/if}

  {#if currentPage < totalPages && !loading}
    <div class="load-more-row">
      <button onclick={handleLoadMore} disabled={loadingMore} class="btn btn--secondary" aria-busy={loadingMore}>
        {loadingMore ? 'Carregando...' : `Página ${currentPage + 1} de ${totalPages}`}
      </button>
    </div>
  {/if}

  {#if currentPage >= totalPages && publications.length > 0 && !loading && !featuredPub}
    <div class="end-summary">
      {publications.length.toLocaleString()} publicações
    </div>
  {/if}

  {#if !loading && publications.length === 0 && !error}
    <div class="card"><div class="card-body empty-text">Nenhuma publicação encontrada.</div></div>
  {/if}
</div>

<style>
  .card {
    background: var(--color-base-100);
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-box);
    margin-bottom: 2rem;
  }

  .card-body {
    padding: 1.5rem;
  }

  .header-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
  }

  .header-info {
    display: flex;
    align-items: center;
    gap: 1.5rem;
    flex-wrap: wrap;
  }

  .date-title {
    margin: 0;
  }

  .badge-accent {
    display: inline-flex;
    align-items: center;
    padding: 0.125rem 0.5rem;
    font-size: var(--font-size-xs);
    font-weight: 500;
    border-radius: var(--radius-full);
    background: var(--color-accent);
    color: var(--color-accent-content);
  }

  .meta-dim {
    opacity: 0.5;
    font-size: var(--font-size-sm);
  }

  .header-actions {
    display: flex;
    gap: 0.5rem;
  }

  .btn-outline-secondary {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.375rem;
    padding: 0.375rem 0.75rem;
    font-size: var(--font-size-xs);
    font-weight: 600;
    border-radius: var(--radius-btn);
    cursor: pointer;
    transition: all var(--transition-base);
    border: 1px solid var(--color-secondary);
    background: transparent;
    color: var(--color-secondary);
    text-decoration: none;
  }

  .btn-outline-secondary:hover {
    background: var(--color-secondary);
    color: var(--color-secondary-content);
  }

  .meta-row {
    display: flex;
    gap: 1.5rem;
    font-size: var(--font-size-xs);
    opacity: 0.5;
    margin-top: 1rem;
  }

  .loading-center {
    display: flex;
    justify-content: center;
    padding: 2rem;
  }

  .spinner {
    border: 2px solid var(--color-base-300);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  .spinner--lg {
    width: 2rem;
    height: 2rem;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .error-text {
    color: var(--color-error);
    text-align: center;
  }

  .empty-text {
    text-align: center;
    opacity: 0.5;
  }

  .btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    font-size: var(--font-size-sm);
    font-weight: 600;
    border-radius: var(--radius-btn);
    cursor: pointer;
    transition: all var(--transition-base);
    border: 1px solid transparent;
    background: var(--color-primary);
    color: var(--color-primary-content);
  }

  .btn--secondary {
    background: var(--color-secondary);
    color: var(--color-secondary-content);
  }

  .load-more-row {
    text-align: center;
    margin-top: 4rem;
  }

  .end-summary {
    text-align: center;
    margin-top: 4rem;
    opacity: 0.5;
    font-size: var(--font-size-sm);
  }
</style>
