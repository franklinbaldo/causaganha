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
    class="btn btn-outline btn-secondary text-xs px-3 py-1.5 inline-flex items-center gap-1.5"
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
  <div class="card bg-base-100 shadow-sm border border-base-300 mb-8">
    <div class="card-body p-6">
      <header class="flex justify-between items-center flex-wrap gap-4">
        <div class="flex items-center gap-6 flex-wrap">
          <h3 class="m-0">{dateStr}</h3>
          {#if zipSize != null}
            <span class="badge badge-accent">{formatSize(zipSize)}</span>
          {/if}
          {#if totalPages > 0}
            <span class="opacity-50 text-sm">{totalPages} pág.</span>
          {/if}
          {#if itemFileCount != null}
            <span class="opacity-50 text-sm">{itemFileCount} arquivos</span>
          {/if}
        </div>
        <div class="flex gap-2" aria-label="Ações do arquivo">
          {@render DateShareButton()}
          <a href={zipUrl} class="btn btn-outline btn-secondary text-xs px-3 py-1.5" target="_blank" rel="noopener noreferrer">Baixar ZIP</a>
          <a href={`https://archive.org/details/${itemId}`} class="btn btn-outline btn-secondary text-xs px-3 py-1.5" target="_blank" rel="noopener noreferrer">Ver no IA</a>
        </div>
      </header>
      <div class="flex gap-6 text-xs opacity-50 mt-4">
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
    <div class="flex justify-center p-8"><span class="loading loading-spinner loading-lg"></span></div>
  {/if}

  {#if error}
    <div class="card bg-base-100 shadow-sm border border-base-300"><div class="card-body text-error text-center">Erro: {error}</div></div>
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
    <div class="text-center mt-16">
      <button onclick={handleLoadMore} disabled={loadingMore} class="btn btn-secondary" aria-busy={loadingMore}>
        {loadingMore ? 'Carregando...' : `Página ${currentPage + 1} de ${totalPages}`}
      </button>
    </div>
  {/if}

  {#if currentPage >= totalPages && publications.length > 0 && !loading && !featuredPub}
    <div class="text-center mt-16 opacity-50 text-sm">
      {publications.length.toLocaleString()} publicações
    </div>
  {/if}

  {#if !loading && publications.length === 0 && !error}
    <div class="card bg-base-100 shadow-sm border border-base-300"><div class="card-body text-center opacity-50">Nenhuma publicação encontrada.</div></div>
  {/if}
</div>
