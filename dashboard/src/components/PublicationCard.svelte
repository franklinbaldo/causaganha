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
  <div class="card" id={`pub-${seq}`}><div class="card-body compact-body">
    <header class="card-header">
      <div class="header-left-stack">
        <div class="header-meta">
          <span class="seq-number">#{seq}</span>
          {#if pub.tipoComunicacao}
            <span class="badge">{pub.tipoComunicacao}</span>
          {/if}
        </div>
        {#if processNumber}
          <span class="process-number process-number-lg">{processNumber}</span>
        {/if}
      </div>
      <button
        class="btn-outline-secondary"
        onclick={(e: MouseEvent) => handleShare(e, 'compact')}
        title="Copiar link"
      >
        {@render shareIcon()}
        {shareCopiedCompact ? 'Copiado!' : 'Link'}
      </button>
    </header>
    {#if pub.nomeOrgao}
      <small class="orgao-name">{pub.nomeOrgao}</small>
    {/if}
    {#if pub.texto}
      <p class="text-preview">
        {pub.texto.length > 300 ? pub.texto.substring(0, 300) + '...' : pub.texto}
      </p>
    {/if}
    {#if pub.destinatarios && pub.destinatarios.length > 0}
      <div class="tags-row">
        {#each pub.destinatarios as d}
          <span class="badge">{d.nome}</span>
        {/each}
      </div>
    {/if}
    {#if pub.destinatarioadvogados && pub.destinatarioadvogados.length > 0}
      <div class="tags-row lawyers-row">
        {#each pub.destinatarioadvogados as da}
          <span class="lawyer-text">
            {da.advogado?.nome} {da.advogado?.numero_oab ? `(OAB ${da.advogado.uf_oab} ${da.advogado.numero_oab})` : ''}
          </span>
        {/each}
      </div>
    {/if}
  </div></div>

{:else if isReaderMode}
  <!-- Reader mode -->
  <div class="card reader-mode" id={`pub-${seq}`}><div class="card-body reader-body">
    <header class="card-header">
      <div class="header-meta">
        <span class="seq-number seq-bold">#{seq}</span>
        <span class="badge">Modo Leitura</span>
        <small class="date-label">{dateStr}</small>
      </div>
      <div class="header-actions" aria-label="Ações de navegação e leitura">
        <button
          class="btn-outline-secondary"
          onclick={() => isReaderMode = false}
          title="Sair do Modo Leitura"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Voltar
        </button>
        <button
          class="btn-outline-secondary"
          onclick={(e: MouseEvent) => handleShare(e, 'reader')}
          title="Copiar link"
        >
          {@render shareIcon()}
          {shareCopiedReader ? 'Copiado!' : 'Compartilhar'}
        </button>
      </div>
    </header>

    {#if processNumber}
      <h2 class="process-number process-number-xl">{processNumber}</h2>
    {/if}
    {#if pub.nomeOrgao}
      <p class="orgao-name-reader">{pub.nomeOrgao}</p>
    {/if}

    <div class="ai-summary-placeholder">
      <div class="ai-summary-header">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="var(--accent-gold)" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
        </svg>
        <strong class="ai-summary-title">Resumo com IA (Em breve)</strong>
      </div>
      <p class="ai-summary-text">
        Esta seção fornecerá um resumo em linguagem clara da decisão e seu resultado.
      </p>
    </div>

    <div class="reader-content">
      {#if textParts.length > 0}
        <div class="reader-text">
          {#each textParts as part}
            <p class="reader-paragraph">
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
  <div class="card" id={`pub-${seq}`}><div class="card-body featured-body">
    <header class="card-header">
      <div class="header-meta">
        <span class="seq-number seq-bold">#{seq}</span>
        {#if pub.tipoComunicacao}
          <span class="badge">{pub.tipoComunicacao}</span>
        {/if}
        <small class="date-label">{dateStr}</small>
      </div>
      <div class="header-actions" aria-label="Ações de navegação e leitura">
        <button
          class="btn-outline-primary"
          onclick={() => isReaderMode = true}
          title="Abrir Modo Leitura"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
          Modo Leitura
        </button>
        <div class="nav-actions" aria-label="Ações de navegação">
          {#if onNavigate}
            <button
              class="btn-outline-secondary"
              onclick={() => onNavigate(seq - 1)}
              disabled={seq <= 1}
            >
              Anterior
            </button>
            <button
              class="btn-outline-secondary"
              onclick={() => onNavigate(seq + 1)}
              disabled={totalSeq != null && seq >= totalSeq}
            >
              Próxima
            </button>
          {/if}
          <button
            class="btn-outline-secondary"
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
      <div class="process-number process-number-lg featured-process">{processNumber}</div>
    {/if}
    {#if pub.nomeOrgao}
      <small class="orgao-name-block">{pub.nomeOrgao}</small>
    {/if}

    {#if textParts.length > 0}
      <div class="text-section">
        {#each textParts as part}
          <p class="text-preview">
            {part}
          </p>
        {/each}
      </div>
    {/if}

    {#if pub.destinatarios && pub.destinatarios.length > 0}
      <footer class="card-footer">
        <strong class="footer-label">Destinatários</strong>
        <div class="tags-row">
          {#each pub.destinatarios as d}
            <span class="badge">{d.nome}</span>
          {/each}
        </div>
      </footer>
    {/if}
    {#if pub.destinatarioadvogados && pub.destinatarioadvogados.length > 0}
      <footer class="card-footer">
        <strong class="footer-label">Advogados</strong>
        <div class="tags-row">
          {#each pub.destinatarioadvogados as da}
            <span class="lawyer-text-sm">
              {da.advogado?.nome} {da.advogado?.numero_oab ? `(OAB ${da.advogado.uf_oab} ${da.advogado.numero_oab})` : ''}
            </span>
          {/each}
        </div>
      </footer>
    {/if}
  </div></div>
{/if}

<style>
  /* Card base */
  .card {
    background: var(--color-base-100);
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-box);
  }

  .card-body {
    padding: 1.5rem;
  }

  .compact-body {
    padding: 1rem;
  }

  .reader-body {
    padding: 1.5rem;
  }

  .featured-body {
    padding: 1.5rem;
  }

  /* Header */
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
    border-bottom: 1px solid var(--color-base-300);
    padding-bottom: 1rem;
    margin-bottom: 1rem;
  }

  .reader-mode .card-header {
    margin-bottom: 1.5rem;
  }

  .featured-body .card-header {
    margin-bottom: 1.5rem;
  }

  .header-left-stack {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .header-meta {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
  }

  .header-actions {
    display: flex;
    gap: 0.5rem;
  }

  .nav-actions {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  /* Seq number */
  .seq-number {
    font-family: var(--font-mono);
    font-size: var(--font-size-xs);
    opacity: 0.5;
  }

  .seq-bold {
    font-weight: 600;
  }

  /* Badge */
  .badge {
    display: inline-flex;
    align-items: center;
    padding: 0.125rem 0.5rem;
    border-radius: var(--radius-full);
    font-size: var(--font-size-xs);
    background: var(--color-base-200, rgba(0, 0, 0, 0.05));
    color: var(--color-base-content);
  }

  /* Date label */
  .date-label {
    opacity: 0.5;
    font-size: var(--font-size-xs);
  }

  /* Process number */
  .process-number {
    color: var(--color-accent);
    font-weight: 600;
    font-family: var(--font-mono);
  }

  .process-number-lg {
    font-size: 1.125rem;
  }

  .process-number-xl {
    font-size: 1.5rem;
    margin-bottom: 0.5rem;
  }

  .featured-process {
    margin-bottom: 1rem;
  }

  /* Buttons */
  .btn-outline-secondary {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    font-size: var(--font-size-xs);
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-btn);
    background: transparent;
    color: var(--color-base-content);
    cursor: pointer;
    transition: var(--transition-base);
    min-height: 1.5rem;
    min-width: 1.5rem;
  }

  .btn-outline-secondary:hover {
    background: var(--color-base-200, rgba(0, 0, 0, 0.05));
  }

  .btn-outline-secondary:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .btn-outline-primary {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    font-size: var(--font-size-xs);
    border: 1px solid var(--color-primary);
    border-radius: var(--radius-btn);
    background: transparent;
    color: var(--color-primary);
    cursor: pointer;
    transition: var(--transition-base);
    min-height: 1.5rem;
    min-width: 1.5rem;
  }

  .btn-outline-primary:hover {
    background: var(--color-primary);
    color: var(--color-base-100);
  }

  /* Orgao name */
  .orgao-name {
    display: block;
    color: var(--color-primary);
    font-weight: 500;
    font-size: var(--font-size-xs);
    margin-bottom: 1rem;
  }

  .orgao-name-reader {
    opacity: 0.5;
    font-size: var(--font-size-sm);
    margin-bottom: 2.5rem;
  }

  .orgao-name-block {
    display: block;
    opacity: 0.5;
    font-size: var(--font-size-xs);
    margin-bottom: 1.5rem;
  }

  /* Text */
  .text-preview {
    font-size: var(--font-size-sm);
    opacity: 0.7;
    line-height: 1.625;
  }

  .text-section {
    border-top: 1px solid var(--color-base-300);
    padding-top: 1.5rem;
  }

  /* Tags */
  .tags-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .lawyers-row {
    margin-top: 0.5rem;
  }

  .lawyer-text {
    font-size: var(--font-size-xs);
    opacity: 0.5;
  }

  .lawyer-text-sm {
    font-size: var(--font-size-sm);
    opacity: 0.7;
  }

  /* Footer */
  .card-footer {
    border-top: 1px solid var(--color-base-300);
    padding-top: 1.5rem;
    margin-top: 1rem;
  }

  .footer-label {
    display: block;
    font-size: var(--font-size-xs);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    opacity: 0.5;
    margin-bottom: 0.5rem;
  }

  /* AI Summary placeholder */
  .ai-summary-placeholder {
    padding: 1rem;
    margin-bottom: 2.5rem;
    border: 1px solid var(--color-base-300);
    border-radius: var(--radius-box);
    background: var(--color-base-200, rgba(0, 0, 0, 0.03));
  }

  .ai-summary-header {
    display: flex;
    align-items: center;
    gap: 1rem;
    margin-bottom: 0.5rem;
  }

  .ai-summary-title {
    font-size: var(--font-size-sm);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--color-accent);
  }

  .ai-summary-text {
    font-size: var(--font-size-sm);
    opacity: 0.7;
    margin: 0;
  }

  /* Reader content */
  .reader-content {
    padding-top: 1.5rem;
  }

  .reader-paragraph {
    font-size: 1.125rem;
    color: var(--color-primary);
    line-height: 2;
    margin-bottom: 1.5rem;
  }
</style>
