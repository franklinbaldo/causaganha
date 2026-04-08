<script lang="ts">
  interface Publication {
    id?: string;
    numero_processo?: string;
    tipoComunicacao?: string;
    nomeOrgao?: string;
    texto?: string;
    destinatarios?: { nome: string }[];
    destinatarioadvogados?: { advogado?: { nome?: string; numero_oab?: string; uf_oab?: string } }[];
  }

  /**
   * Format a raw process number into the standard CNJ pattern.
   * Input:  "7019279602020822001" or "70192796020208220001"
   * Output: "7019279-60.2020.8.22.0001"
   * Pattern: NNNNNNN-DD.AAAA.J.TR.OOOO
   */
  function formatProcessNumber(raw: string | undefined | null): string | null {
    if (!raw) return null;
    if (raw.includes('-')) return raw;
    const digits = raw.replace(/\D/g, '');
    if (digits.length === 20) {
      return `${digits.slice(0, 7)}-${digits.slice(7, 9)}.${digits.slice(9, 13)}.${digits.slice(13, 14)}.${digits.slice(14, 16)}.${digits.slice(16, 20)}`;
    }
    return raw;
  }

  /**
   * Parse publication text into structured paragraphs.
   */
  function parseText(text: string | undefined | null): string[] {
    if (!text) return [];
    const markers = /(?=(?:Processo\s*:|Classe\s*:|INTIMA[CÇ][AÃ]O|CITA[CÇ][AÃ]O|DESPACHO|DECIS[AÃ]O|SENTEN[CÇ]A|EDITAL|Designada\s+AUDI[EÊ]NCIA|DATA\s+E\s+HORA))/gi;
    const parts = text.split(markers).map(p => p.trim()).filter(Boolean);
    return parts.length > 1 ? parts : [text];
  }

  function escapeRegExp(string: string): string {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  interface HighlightTerm {
    text: string;
    type: 'party' | 'lawyer';
  }

  function highlightText(part: string, terms: HighlightTerm[]): { token: string; type?: 'party' | 'lawyer' }[] {
    if (terms.length === 0) {
      return [{ token: part }];
    }

    terms.sort((a, b) => b.text.length - a.text.length);

    const termMap = new Map<string, 'party' | 'lawyer'>();
    terms.forEach(t => termMap.set(t.text.toLowerCase(), t.type));

    const pattern = terms.map(t => escapeRegExp(t.text)).join('|');
    const regex = new RegExp(`(${pattern})`, 'gi');

    const tokens = part.split(regex);

    return tokens.map(token => {
      const type = termMap.get(token.toLowerCase());
      return type ? { token, type } : { token };
    });
  }

  function buildTerms(pub: Publication): HighlightTerm[] {
    const terms: HighlightTerm[] = [];
    if (pub.destinatarios) {
      pub.destinatarios.forEach(d => {
        if (d.nome && d.nome.length > 3) {
          terms.push({ text: d.nome, type: 'party' });
        }
      });
    }
    if (pub.destinatarioadvogados) {
      pub.destinatarioadvogados.forEach(da => {
        if (da.advogado?.nome && da.advogado.nome.length > 3) {
          terms.push({ text: da.advogado.nome, type: 'lawyer' });
        }
      });
    }
    return terms;
  }

  let {
    pub,
    seq,
    dateStr,
    page,
    compact = false,
    totalSeq,
    onNavigate,
  }: {
    pub: Publication;
    seq: number;
    dateStr: string;
    page?: number;
    compact?: boolean;
    totalSeq?: number;
    onNavigate?: (newSeq: number) => void;
  } = $props();

  let isReaderMode = $state(false);
  let shareCopied = $state(false);
  let shareCopiedReader = $state(false);
  let shareCopiedCompact = $state(false);

  const processNumber = $derived(formatProcessNumber(pub.numero_processo));
  const textParts = $derived(parseText(pub.texto));
  const terms = $derived(buildTerms(pub));

  function handleShare(e: MouseEvent, copiedSetter: 'main' | 'reader' | 'compact') {
    e.preventDefault();
    e.stopPropagation();
    const base = window.location.pathname;
    let hash = dateStr;
    if (page) hash += `/${page}`;
    if (seq) hash += `/${seq}`;
    const url = `${window.location.origin}${base}#${hash}`;
    navigator.clipboard?.writeText(url);
    if (copiedSetter === 'main') {
      shareCopied = true;
      setTimeout(() => shareCopied = false, 2000);
    } else if (copiedSetter === 'reader') {
      shareCopiedReader = true;
      setTimeout(() => shareCopiedReader = false, 2000);
    } else {
      shareCopiedCompact = true;
      setTimeout(() => shareCopiedCompact = false, 2000);
    }
  }
</script>

{#snippet shareIcon()}
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
    <path stroke-linecap="round" stroke-linejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
  </svg>
{/snippet}

{#if compact}
  <!-- Compact view -->
  <div class="card bg-base-100 shadow-sm border border-base-300" id={`pub-${seq}`}><div class="card-body p-4">
    <header class="flex justify-between items-baseline items-center border-b border-base-300 pb-4 mb-4 flex-wrap gap-4">
      <div class="flex flex-col gap-2">
        <div class="flex items-center gap-4 flex-wrap">
          <span class="font-mono text-xs opacity-50">#{seq}</span>
          {#if pub.tipoComunicacao}
            <span class="badge">{pub.tipoComunicacao}</span>
          {/if}
        </div>
        {#if processNumber}
          <span class="text-accent text-lg font-semibold font-mono">{processNumber}</span>
        {/if}
      </div>
      <button
        class="btn btn-outline btn-secondary text-xs px-4 py-2 inline-flex items-center gap-2"
        onclick={(e: MouseEvent) => handleShare(e, 'compact')}
        title="Copiar link"
      >
        {@render shareIcon()}
        {shareCopiedCompact ? 'Copiado!' : 'Link'}
      </button>
    </header>
    {#if pub.nomeOrgao}
      <small class="text-primary font-medium text-xs block mb-4">{pub.nomeOrgao}</small>
    {/if}
    {#if pub.texto}
      <p class="text-sm opacity-70 leading-relaxed">
        {pub.texto.length > 300 ? pub.texto.substring(0, 300) + '...' : pub.texto}
      </p>
    {/if}
    {#if pub.destinatarios && pub.destinatarios.length > 0}
      <div class="flex flex-wrap gap-2">
        {#each pub.destinatarios as d}
          <span class="badge">{d.nome}</span>
        {/each}
      </div>
    {/if}
    {#if pub.destinatarioadvogados && pub.destinatarioadvogados.length > 0}
      <div class="flex flex-wrap gap-2 mt-2">
        {#each pub.destinatarioadvogados as da}
          <span class="text-xs opacity-50">
            {da.advogado?.nome} {da.advogado?.numero_oab ? `(OAB ${da.advogado.uf_oab} ${da.advogado.numero_oab})` : ''}
          </span>
        {/each}
      </div>
    {/if}
  </div></div>

{:else if isReaderMode}
  <!-- Reader mode -->
  <div class="card bg-base-100 shadow-sm border border-base-300 reader-mode" id={`pub-${seq}`}><div class="card-body p-6">
    <header class="flex justify-between items-baseline flex-wrap gap-4 border-b border-base-300 pb-4 mb-6 items-center">
      <div class="flex items-center flex-wrap gap-4">
        <span class="font-mono text-xs font-semibold opacity-50">#{seq}</span>
        <span class="badge">Modo Leitura</span>
        <small class="opacity-50 text-xs">{dateStr}</small>
      </div>
      <div class="flex gap-2" aria-label="Ações de navegação e leitura">
        <button
          class="btn btn-outline btn-secondary text-xs px-4 py-2 inline-flex items-center gap-2 min-h-6 min-w-6"
          onclick={() => isReaderMode = false}
          title="Sair do Modo Leitura"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Voltar
        </button>
        <button
          class="btn btn-outline btn-secondary text-xs px-4 py-2 inline-flex items-center gap-2"
          onclick={(e: MouseEvent) => handleShare(e, 'reader')}
          title="Copiar link"
        >
          {@render shareIcon()}
          {shareCopiedReader ? 'Copiado!' : 'Compartilhar'}
        </button>
      </div>
    </header>

    {#if processNumber}
      <h2 class="text-accent text-2xl font-semibold font-mono mb-2">{processNumber}</h2>
    {/if}
    {#if pub.nomeOrgao}
      <p class="opacity-50 text-sm mb-10">{pub.nomeOrgao}</p>
    {/if}

    <div class="ai-summary-placeholder p-4 mb-10 border rounded bg-surface-overlay">
      <div class="flex items-center gap-4 mb-2">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="var(--accent-gold)" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        <strong class="text-sm uppercase tracking-widest text-accent">Resumo com IA (Em breve)</strong>
      </div>
      <p class="text-sm opacity-70 m-0">
        Esta seção fornecerá um resumo em linguagem clara da decisão e seu resultado.
      </p>
    </div>

    <div class="reader-content pt-6">
      {#if textParts.length > 0}
        <div class="reader-text">
          {#each textParts as part}
            <p class="text-lg text-primary leading-loose mb-6">
              {#each highlightText(part, terms) as segment}
                {#if segment.type}
                  <mark class={segment.type === 'party' ? 'entity-party' : 'entity-lawyer'}>{segment.token}</mark>
                {:else}
                  {segment.token}
                {/if}
              {/each}
            </p>
          {/each}
        </div>
      {/if}
    </div>
  </div></div>

{:else}
  <!-- Full / featured view -->
  <div class="card bg-base-100 shadow-sm border border-base-300" id={`pub-${seq}`}><div class="card-body p-6">
    <header class="flex justify-between items-baseline flex-wrap gap-4 border-b border-base-300 pb-4 mb-6 items-center">
      <div class="flex items-center flex-wrap gap-4">
        <span class="font-mono text-xs font-semibold opacity-50">#{seq}</span>
        {#if pub.tipoComunicacao}
          <span class="badge">{pub.tipoComunicacao}</span>
        {/if}
        <small class="opacity-50 text-xs">{dateStr}</small>
      </div>
      <div class="flex gap-2" aria-label="Ações de navegação e leitura">
        <button
          class="btn btn-outline btn-primary text-xs px-4 py-2 inline-flex items-center gap-2 min-h-6 min-w-6"
          onclick={() => isReaderMode = true}
          title="Abrir Modo Leitura"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          Modo Leitura
        </button>
        <div class="flex items-center gap-2" aria-label="Ações de navegação">
          {#if onNavigate}
            <button
              class="btn btn-outline btn-secondary text-xs px-4 py-2"
              onclick={() => onNavigate(seq - 1)}
              disabled={seq <= 1}
            >
              Anterior
            </button>
            <button
              class="btn btn-outline btn-secondary text-xs px-4 py-2"
              onclick={() => onNavigate(seq + 1)}
              disabled={totalSeq != null && seq >= totalSeq}
            >
              Próxima
            </button>
          {/if}
          <button
            class="btn btn-outline btn-secondary text-xs px-4 py-2 inline-flex items-center gap-2"
            onclick={(e: MouseEvent) => handleShare(e, 'main')}
            title="Copiar link"
          >
            {@render shareIcon()}
            {shareCopied ? 'Copiado!' : 'Compartilhar'}
          </button>
        </div>
      </div>
    </header>

    {#if processNumber}
      <div class="text-accent text-lg font-semibold font-mono mb-4">{processNumber}</div>
    {/if}
    {#if pub.nomeOrgao}
      <small class="block opacity-50 text-xs mb-6">{pub.nomeOrgao}</small>
    {/if}

    {#if textParts.length > 0}
      <div class="border-t border-base-300 pt-6">
        {#each textParts as part}
          <p class="text-sm opacity-70 leading-relaxed">
            {part}
          </p>
        {/each}
      </div>
    {/if}

    {#if pub.destinatarios && pub.destinatarios.length > 0}
      <footer class="border-t border-base-300 pt-6 mt-4">
        <strong class="text-xs uppercase tracking-widest opacity-50 block mb-2">Destinatários</strong>
        <div class="flex flex-wrap gap-2">
          {#each pub.destinatarios as d}
            <span class="badge">{d.nome}</span>
          {/each}
        </div>
      </footer>
    {/if}
    {#if pub.destinatarioadvogados && pub.destinatarioadvogados.length > 0}
      <footer class="border-t border-base-300 pt-6 mt-4">
        <strong class="text-xs uppercase tracking-widest opacity-50 block mb-2">Advogados</strong>
        <div class="flex flex-wrap gap-2">
          {#each pub.destinatarioadvogados as da}
            <span class="text-sm opacity-70">
              {da.advogado?.nome} {da.advogado?.numero_oab ? `(OAB ${da.advogado.uf_oab} ${da.advogado.numero_oab})` : ''}
            </span>
          {/each}
        </div>
      </footer>
    {/if}
  </div></div>
{/if}
