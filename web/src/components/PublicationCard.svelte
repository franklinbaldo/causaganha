<script lang="ts">
  import type { DjenPublication } from "../lib/djen";

  interface HighlightTerm {
    text: string;
    type: "party" | "lawyer";
  }

  interface MetaChip {
    label: string;
    value: string;
    tone?: "default" | "accent" | "success" | "warning" | "danger";
  }

  function formatProcessNumber(raw: string | undefined | null): string | null {
    if (!raw) return null;
    if (raw.includes("-")) return raw;
    const digits = raw.replace(/\D/g, "");
    if (digits.length === 20) {
      return `${digits.slice(0, 7)}-${digits.slice(7, 9)}.${digits.slice(9, 13)}.${digits.slice(13, 14)}.${digits.slice(14, 16)}.${digits.slice(16, 20)}`;
    }
    return raw;
  }

  function parseText(text: string | undefined | null): string[] {
    if (!text) return [];
    const markers =
      /(?=(?:Processo\s*:|Classe\s*:|INTIMA(?:\u00c7\u00c3O|CAO)|CITA(?:\u00c7\u00c3O|CAO)|DESPACHO|DECIS(?:\u00c3O|AO)|SENTEN(?:\u00c7A|CA)|EDITAL|Designada\s+AUDI(?:\u00caNCIA|ENCIA)|DATA\s+E\s+HORA))/gi;
    const parts = text
      .split(markers)
      .map((part) => part.trim())
      .filter(Boolean);
    return parts.length > 1 ? parts : [text];
  }

  function escapeRegExp(value: string): string {
    return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function highlightText(
    part: string,
    terms: HighlightTerm[],
  ): { token: string; type?: "party" | "lawyer" }[] {
    if (terms.length === 0) {
      return [{ token: part }];
    }

    const sortedTerms = [...terms].sort((a, b) => b.text.length - a.text.length);
    const termMap = new Map<string, "party" | "lawyer">();
    sortedTerms.forEach((term) => termMap.set(term.text.toLowerCase(), term.type));

    const pattern = sortedTerms.map((term) => escapeRegExp(term.text)).join("|");
    const regex = new RegExp(`(${pattern})`, "gi");

    return part.split(regex).map((token) => {
      const type = termMap.get(token.toLowerCase());
      return type ? { token, type } : { token };
    });
  }

  function buildTerms(pub: DjenPublication): HighlightTerm[] {
    const terms: HighlightTerm[] = [];

    pub.destinatarios?.forEach((destinatario) => {
      if (destinatario.nome && destinatario.nome.length > 3) {
        terms.push({ text: destinatario.nome, type: "party" });
      }
    });

    pub.destinatarioadvogados?.forEach((entry) => {
      if (entry.advogado?.nome && entry.advogado.nome.length > 3) {
        terms.push({ text: entry.advogado.nome, type: "lawyer" });
      }
    });

    return terms;
  }

  function previewText(text: string | undefined, limit = 320): string | null {
    if (!text) return null;
    const cleaned = text.replace(/\s+/g, " ").trim();
    if (cleaned.length <= limit) return cleaned;
    return `${cleaned.slice(0, limit).trimEnd()}...`;
  }

  function htmlToPreviewText(html: string | undefined, limit = 320): string | null {
    if (!html) return null;

    const text = html
      .replace(/<br\s*\/?>/gi, " ")
      .replace(/<\/(p|div|li|tr|td|th|h[1-6])>/gi, " ")
      .replace(/<[^>]+>/g, " ")
      .replace(/&nbsp;/gi, " ")
      .replace(/&amp;/gi, "&")
      .replace(/&lt;/gi, "<")
      .replace(/&gt;/gi, ">")
      .replace(/&quot;/gi, '"')
      .replace(/&#39;/gi, "'");

    return previewText(text, limit);
  }

  function summarizeMedium(pub: DjenPublication): string | null {
    if (pub.meiocompleto) return pub.meiocompleto;
    if (pub.meio === "D") return "Diário Eletrônico";
    if (pub.meio === "E") return "Edital";
    return null;
  }

  function summarizeStatus(pub: DjenPublication): MetaChip | null {
    if (pub.ativo === false || pub.motivo_cancelamento) {
      return { label: "Status", value: "Cancelada", tone: "danger" };
    }
    if (pub.status === "P") {
      return { label: "Status", value: "Publicada", tone: "success" };
    }
    if (pub.status) {
      return { label: "Status", value: pub.status, tone: "warning" };
    }
    if (pub.ativo === true) {
      return { label: "Status", value: "Ativa", tone: "success" };
    }
    return null;
  }

  function buildMetaChips(pub: DjenPublication): MetaChip[] {
    const chips: MetaChip[] = [];
    const statusChip = summarizeStatus(pub);
    const medium = summarizeMedium(pub);

    if (statusChip) chips.push(statusChip);
    if (pub.siglaTribunal) chips.push({ label: "Tribunal", value: pub.siglaTribunal });
    if (medium) chips.push({ label: "Meio", value: medium, tone: "accent" });
    if (pub.nomeClasse) chips.push({ label: "Classe", value: pub.nomeClasse });
    if (pub.tipoDocumento) chips.push({ label: "Documento", value: pub.tipoDocumento });
    if (pub.numeroComunicacao != null) {
      chips.push({ label: "Comunicação", value: String(pub.numeroComunicacao) });
    }

    return chips;
  }

  function buildIdentityRows(pub: DjenPublication): MetaChip[] {
    const rows: MetaChip[] = [];

    if (pub.data_disponibilizacao) {
      rows.push({ label: "Disponibilização", value: pub.data_disponibilizacao });
    }
    if (pub.codigoClasse) {
      rows.push({ label: "Código da classe", value: pub.codigoClasse });
    }
    if (pub.hash) {
      rows.push({ label: "Hash", value: pub.hash.slice(0, 16) });
    }
    if (pub.numeroprocessocommascara && pub.numeroprocessocommascara !== pub.numero_processo) {
      rows.push({ label: "Processo mascarado", value: pub.numeroprocessocommascara });
    }

    return rows;
  }

  function uniquePartyNames(pub: DjenPublication): string[] {
    const seen = new Set<string>();
    const names: string[] = [];

    pub.destinatarios?.forEach((destinatario) => {
      if (!destinatario.nome) return;
      const key = destinatario.nome.trim().toLowerCase();
      if (!key || seen.has(key)) return;
      seen.add(key);
      names.push(destinatario.nome);
    });

    return names;
  }

  function uniqueLawyers(pub: DjenPublication): string[] {
    const seen = new Set<string>();
    const lawyers: string[] = [];

    pub.destinatarioadvogados?.forEach((entry) => {
      const advogado = entry.advogado;
      if (!advogado?.nome) return;
      const oab = advogado.numero_oab ? `OAB ${advogado.uf_oab ?? ""} ${advogado.numero_oab}`.trim() : null;
      const label = oab ? `${advogado.nome} (${oab})` : advogado.nome;
      const key = label.toLowerCase();
      if (seen.has(key)) return;
      seen.add(key);
      lawyers.push(label);
    });

    return lawyers;
  }

  let {
    pub,
    seq,
    dateStr,
    page,
    compact = false,
    totalSeq,
    onNavigate,
    onExpand,
    onCollapse,
    source,
    usedFallback,
  }: {
    pub: DjenPublication;
    seq: number;
    dateStr: string;
    page?: number;
    compact?: boolean;
    totalSeq?: number;
    onNavigate?: (newSeq: number) => void;
    onExpand?: () => void;
    onCollapse?: () => void;
    source?: "djen" | "ia";
    usedFallback?: boolean;
  } = $props();

  let isReaderMode = $state(false);
  let activeCopied = $state<"main" | "reader" | "compact" | null>(null);
  let shareTimeoutId: ReturnType<typeof setTimeout> | null = null;

  $effect(() => {
    return () => {
      if (shareTimeoutId) clearTimeout(shareTimeoutId);
    };
  });

  const processNumber = $derived(formatProcessNumber(pub.numero_processo));
  const textParts = $derived(pub.textoRender?.kind === "text" ? parseText(pub.textoRender.content) : []);
  const terms = $derived(buildTerms(pub));
  const teaser = $derived(
    pub.textoRender?.kind === "text" ? previewText(pub.textoRender.content, compact ? 220 : 420) : null,
  );
  const htmlTeaser = $derived(
    pub.textoRender?.kind === "html" ? htmlToPreviewText(pub.textoRender.content, compact ? 220 : 420) : null,
  );
  const metaChips = $derived(buildMetaChips(pub));
  const identityRows = $derived(buildIdentityRows(pub));
  const parties = $derived(uniquePartyNames(pub));
  const lawyers = $derived(uniqueLawyers(pub));

  async function copyToClipboard(text: string): Promise<boolean> {
    if (navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(text);
        return true;
      } catch {
        // fall through to legacy path
      }
    }
    try {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch {
      return false;
    }
  }

  async function handleShare(e: MouseEvent, context: "main" | "reader" | "compact") {
    e.preventDefault();
    e.stopPropagation();
    const base = window.location.pathname;
    let hash = dateStr;
    if (page) hash += `/${page}`;
    if (seq) hash += `/${seq}`;
    const url = `${window.location.origin}${base}#${hash}`;
    const ok = await copyToClipboard(url);
    if (!ok) return;
    if (shareTimeoutId) clearTimeout(shareTimeoutId);
    activeCopied = context;
    shareTimeoutId = setTimeout(() => {
      activeCopied = null;
      shareTimeoutId = null;
    }, 2000);
  }
</script>

{#snippet shareIcon()}
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
    <path stroke-linecap="round" stroke-linejoin="round" d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
  </svg>
{/snippet}

{#snippet openExternalIcon()}
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
    <path stroke-linecap="round" stroke-linejoin="round" d="M14 3h7m0 0v7m0-7L10 14" />
    <path stroke-linecap="round" stroke-linejoin="round" d="M21 14v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
  </svg>
{/snippet}

{#snippet sourceBadge()}
  {#if source}
    <span
      class="badge {source === 'djen' ? 'badge-info' : 'badge-warning'}"
      title={usedFallback ? 'Falha ao conectar no DJEN, usando arquivo IA' : ''}
    >
      Fonte: {source === 'djen' ? 'DJEN' : 'Arquivo IA'}
    </span>
  {/if}
{/snippet}

{#snippet chip(meta: MetaChip)}
  <span class={`meta-chip ${meta.tone ?? "default"}`}>
    <small>{meta.label}</small>
    <strong>{meta.value}</strong>
  </span>
{/snippet}

{#if compact}
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
  <div
    class="card publication-card compact-card"
    class:expandable={!!onExpand}
    id={`pub-${seq}`}
    role={onExpand ? "button" : undefined}
    tabindex={onExpand ? 0 : undefined}
    onclick={(e: MouseEvent) => {
      if ((e.target as HTMLElement).closest("a, button")) return;
      onExpand?.();
    }}
    onkeydown={(e: KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onExpand?.();
      }
    }}
  >
    <div class="card-body compact-body">
      <header class="card-header">
        <div class="header-left-stack">
          <div class="header-meta">
            <span class="seq-number">#{seq}</span>
            {#if pub.tipoComunicacao}
              <span class="badge publication-badge">{pub.tipoComunicacao}</span>
            {/if}
            {@render sourceBadge()}
            <small class="date-label">{dateStr}</small>
          </div>
          {#if processNumber}
            <button
              type="button"
              class="process-number process-number-lg process-link"
              onclick={(e: MouseEvent) => { e.stopPropagation(); onExpand?.(); }}
              title="Abrir detalhes da publicação"
            >{processNumber}</button>
          {/if}
        </div>
        <div class="header-actions">
          {#if pub.link}
            <a class="btn btn-outline-secondary" href={pub.link} target="_blank" rel="noopener noreferrer">
              {@render openExternalIcon()}
              Inteiro teor
            </a>
          {/if}
          <button
            class="btn btn-outline-secondary"
            onclick={(e: MouseEvent) => handleShare(e, "compact")}
            title="Copiar link"
          >
            {@render shareIcon()}
            {activeCopied === "compact" ? "Copiado!" : "Link"}
          </button>
        </div>
      </header>

      {#if metaChips.length > 0}
        <div class="meta-chip-row">
          {#each metaChips as meta}
            {@render chip(meta)}
          {/each}
        </div>
      {/if}

      {#if pub.nomeOrgao}
        <small class="orgao-name">{pub.nomeOrgao}</small>
      {/if}

      {#if pub.textoRender?.kind === "html" && htmlTeaser}
        <p class="text-preview">{htmlTeaser}</p>
      {:else if teaser}
        <p class="text-preview">{teaser}</p>
      {/if}

      <div class="summary-bar">
        {#if parties.length > 0}
          <span>{parties.length} parte{parties.length > 1 ? "s" : ""}</span>
        {/if}
        {#if lawyers.length > 0}
          <span>{lawyers.length} advogado{lawyers.length > 1 ? "s" : ""}</span>
        {/if}
      </div>

      {#if parties.length > 0}
        <div class="tags-row">
          {#each parties.slice(0, 4) as party}
            <span class="badge name-pill">{party}</span>
          {/each}
        </div>
      {/if}
    </div>
  </div>
{:else if isReaderMode}
  <div class="card publication-card reader-mode" id={`pub-${seq}`}>
    <div class="card-body reader-body">
      <header class="card-header">
        <div class="header-left-stack">
          <div class="header-meta">
            <span class="seq-number seq-bold">#{seq}</span>
            <span class="badge publication-badge">Modo Leitura</span>
            {@render sourceBadge()}
            <small class="date-label">{dateStr}</small>
          </div>
          {#if processNumber}
            <h2 class="process-number process-number-xl">{processNumber}</h2>
          {/if}
          {#if pub.nomeOrgao}
            <p class="orgao-name-reader">{pub.nomeOrgao}</p>
          {/if}
        </div>
        <div class="header-actions" aria-label="Ações de navegação e leitura">
          <button
            class="btn btn-outline-secondary"
            onclick={() => (isReaderMode = false)}
            title="Sair do Modo Leitura"
          >
            Voltar
          </button>
          {#if pub.link}
            <a class="btn btn-outline-secondary" href={pub.link} target="_blank" rel="noopener noreferrer">
              {@render openExternalIcon()}
              Inteiro teor
            </a>
          {/if}
          <button
            class="btn btn-outline-secondary"
            onclick={(e: MouseEvent) => handleShare(e, "reader")}
            title="Copiar link"
          >
            {@render shareIcon()}
            {activeCopied === "reader" ? "Copiado!" : "Compartilhar"}
          </button>
        </div>
      </header>

      {#if metaChips.length > 0}
        <div class="meta-chip-row meta-chip-row-spacious">
          {#each metaChips as meta}
            {@render chip(meta)}
          {/each}
        </div>
      {/if}

      <div class="reader-layout">
        <aside class="reader-sidebar">
          {#if identityRows.length > 0}
            <div class="sidebar-panel">
              <strong class="sidebar-title">Metadados</strong>
              <dl class="identity-list">
                {#each identityRows as item}
                  <div class="identity-row">
                    <dt>{item.label}</dt>
                    <dd>{item.value}</dd>
                  </div>
                {/each}
              </dl>
            </div>
          {/if}

          <div class="sidebar-panel">
            <strong class="sidebar-title">Envolvidos</strong>
            <div class="sidebar-tags">
              {#if parties.length > 0}
                {#each parties as party}
                  <span class="badge name-pill">{party}</span>
                {/each}
              {/if}
              {#if lawyers.length > 0}
                {#each lawyers as lawyer}
                  <span class="badge lawyer-pill">{lawyer}</span>
                {/each}
              {/if}
            </div>
          </div>
        </aside>

        <div class="reader-content">
          {#if pub.textoRender?.kind === "html"}
            <div class="html-content html-content-reader">
              {@html pub.textoRender.content}
            </div>
          {:else if textParts.length > 0}
            <div class="reader-text">
              {#each textParts as part}
                <p class="reader-paragraph">
                  {#each highlightText(part, terms) as segment}
                    {#if segment.type}
                      <mark class={segment.type === "party" ? "entity-party" : "entity-lawyer"}>{segment.token}</mark>
                    {:else}
                      {segment.token}
                    {/if}
                  {/each}
                </p>
              {/each}
            </div>
          {/if}
        </div>
      </div>
    </div>
  </div>
{:else}
  <div class="card publication-card featured-card" id={`pub-${seq}`}>
    <div class="card-body featured-body">
      <header class="card-header">
        <div class="header-left-stack">
          <div class="header-meta">
            <span class="seq-number seq-bold">#{seq}</span>
            {#if pub.tipoComunicacao}
              <span class="badge publication-badge">{pub.tipoComunicacao}</span>
            {/if}
            {@render sourceBadge()}
            <small class="date-label">{dateStr}</small>
          </div>
          {#if processNumber}
            <div class="process-number process-number-lg featured-process">{processNumber}</div>
          {/if}
          {#if pub.nomeOrgao}
            <small class="orgao-name-block">{pub.nomeOrgao}</small>
          {/if}
        </div>

        <div class="header-actions" aria-label="Ações de navegação e leitura">
          {#if onCollapse}
            <button
              class="btn btn-outline-secondary"
              onclick={onCollapse}
              title="Fechar detalhes"
            >
              Fechar
            </button>
          {/if}
          <button
            class="btn btn-outline-primary"
            onclick={() => (isReaderMode = true)}
            title="Abrir Modo Leitura"
          >
            Modo Leitura
          </button>
          {#if pub.link}
            <a class="btn btn-outline-secondary" href={pub.link} target="_blank" rel="noopener noreferrer">
              {@render openExternalIcon()}
              Inteiro teor
            </a>
          {/if}
          <div class="nav-actions" aria-label="Ações de navegação">
            {#if onNavigate}
              <button
                class="btn btn-outline-secondary"
                onclick={() => onNavigate(seq - 1)}
                disabled={seq <= 1}
              >
                Anterior
              </button>
              <button
                class="btn btn-outline-secondary"
                onclick={() => onNavigate(seq + 1)}
                disabled={totalSeq != null && seq >= totalSeq}
              >
                Próxima
              </button>
            {/if}
            <button
              class="btn btn-outline-secondary"
              onclick={(e: MouseEvent) => handleShare(e, "main")}
              title="Copiar link"
            >
              {@render shareIcon()}
              {activeCopied === "main" ? "Copiado!" : "Compartilhar"}
            </button>
          </div>
        </div>
      </header>

      {#if metaChips.length > 0}
        <div class="meta-chip-row meta-chip-row-spacious">
          {#each metaChips as meta}
            {@render chip(meta)}
          {/each}
        </div>
      {/if}

      <div class="story-grid">
        <section class="lead-panel">
          {#if teaser}
            <p class="lead-text">{teaser}</p>
          {/if}

          {#if pub.textoRender?.kind === "html"}
            <div class="html-content html-content-featured">
              {@html pub.textoRender.content}
            </div>
          {:else if textParts.length > 0}
            <div class="text-section">
              {#each textParts.slice(0, 3) as part}
                <p class="text-preview">{part}</p>
              {/each}
            </div>
          {/if}
        </section>

        <aside class="detail-panel">
          {#if identityRows.length > 0}
            <div class="sidebar-panel">
              <strong class="sidebar-title">Identificação</strong>
              <dl class="identity-list">
                {#each identityRows as item}
                  <div class="identity-row">
                    <dt>{item.label}</dt>
                    <dd>{item.value}</dd>
                  </div>
                {/each}
              </dl>
            </div>
          {/if}

          {#if parties.length > 0}
            <div class="sidebar-panel">
              <strong class="sidebar-title">Destinatários</strong>
              <div class="sidebar-tags">
                {#each parties as party}
                  <span class="badge name-pill">{party}</span>
                {/each}
              </div>
            </div>
          {/if}

          {#if lawyers.length > 0}
            <div class="sidebar-panel">
              <strong class="sidebar-title">Advogados</strong>
              <div class="sidebar-tags">
                {#each lawyers as lawyer}
                  <span class="badge lawyer-pill">{lawyer}</span>
                {/each}
              </div>
            </div>
          {/if}
        </aside>
      </div>
    </div>
  </div>
{/if}

<style>
  .publication-card {
    overflow: hidden;
    background:
      radial-gradient(circle at top left, rgba(180, 83, 9, 0.08), transparent 26rem),
      linear-gradient(180deg, var(--color-surface-raised), transparent 12rem),
      var(--color-base-100);
  }

  .compact-card {
    margin-bottom: 1rem;
  }

  .expandable {
    cursor: pointer;
    transition: border-color var(--transition-base), box-shadow var(--transition-base);
  }

  .expandable:hover {
    border-color: var(--color-accent);
    box-shadow: var(--shadow-md);
  }

  .compact-body {
    padding: 1.25rem;
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 1rem;
    border-bottom: 1px solid var(--color-base-300);
    padding-bottom: 1rem;
    margin-bottom: 1rem;
  }

  .header-left-stack {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    min-width: 0;
  }

  .header-meta,
  .header-actions,
  .nav-actions,
  .meta-chip-row,
  .tags-row,
  .sidebar-tags,
  .summary-bar {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .header-meta {
    align-items: center;
    gap: 0.75rem;
  }

  .header-actions {
    justify-content: flex-end;
  }

  .nav-actions {
    align-items: center;
  }

  .seq-number {
    font-family: var(--font-mono);
    font-size: var(--font-size-xs);
    opacity: 0.5;
  }

  .seq-bold {
    font-weight: 700;
  }

  .publication-badge {
    background: var(--color-primary);
    color: var(--color-primary-content);
  }

  .date-label {
    opacity: 0.6;
    font-size: var(--font-size-xs);
  }

  .process-number {
    color: var(--color-accent);
    font-weight: 700;
    font-family: var(--font-mono);
    letter-spacing: -0.03em;
  }

  .process-link {
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    text-decoration: underline;
    text-decoration-color: transparent;
    text-underline-offset: 0.15em;
    transition: text-decoration-color var(--transition-base), color var(--transition-base);
  }

  .process-link:hover {
    color: var(--color-primary);
    text-decoration-color: var(--color-primary);
  }

  .process-number-lg {
    font-size: 1.125rem;
  }

  .process-number-xl {
    font-size: 1.5rem;
    margin: 0;
  }

  .featured-process {
    margin-bottom: 0;
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

  .meta-chip-row {
    margin-bottom: 1rem;
  }

  .meta-chip-row-spacious {
    margin-bottom: 1.5rem;
  }

  .meta-chip {
    display: inline-flex;
    flex-direction: column;
    gap: 0.15rem;
    min-width: 7rem;
    padding: 0.65rem 0.8rem;
    border: 1px solid var(--color-base-300);
    border-radius: 0.85rem;
    background: var(--color-surface);
    backdrop-filter: blur(6px);
  }

  .meta-chip small {
    font-size: 0.65rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.55;
  }

  .meta-chip strong {
    font-size: var(--font-size-sm);
    line-height: 1.2;
    color: var(--color-primary);
  }

  .meta-chip.accent {
    border-color: color-mix(in srgb, var(--color-accent) 30%, transparent);
    background: color-mix(in srgb, var(--color-accent) 8%, transparent);
  }

  .meta-chip.success {
    border-color: color-mix(in srgb, var(--color-success) 25%, transparent);
    background: color-mix(in srgb, var(--color-success) 8%, transparent);
  }

  .meta-chip.warning {
    border-color: color-mix(in srgb, var(--color-warning) 25%, transparent);
    background: color-mix(in srgb, var(--color-warning) 8%, transparent);
  }

  .meta-chip.danger {
    border-color: color-mix(in srgb, var(--color-error) 25%, transparent);
    background: color-mix(in srgb, var(--color-error) 8%, transparent);
  }

  .orgao-name,
  .orgao-name-reader,
  .orgao-name-block {
    display: block;
    color: var(--color-primary);
  }

  .orgao-name {
    font-size: var(--font-size-xs);
    font-weight: 600;
    margin-bottom: 0.9rem;
  }

  .orgao-name-reader,
  .orgao-name-block {
    opacity: 0.6;
    font-size: var(--font-size-sm);
  }

  .lead-text {
    font-size: var(--font-size-md);
    line-height: 1.8;
    color: var(--color-primary);
    margin-bottom: 1rem;
  }

  .text-preview {
    font-size: var(--font-size-sm);
    opacity: 0.78;
    line-height: 1.7;
  }

  .text-section {
    display: grid;
    gap: 0.85rem;
    border-top: 1px solid var(--color-base-300);
    padding-top: 1.2rem;
  }

  .summary-bar {
    margin: 1rem 0 0.75rem;
    font-size: var(--font-size-xs);
    color: var(--color-content-secondary);
  }

  .story-grid,
  .reader-layout {
    display: grid;
    gap: 1.25rem;
    grid-template-columns: minmax(0, 1.65fr) minmax(18rem, 1fr);
  }

  .lead-panel,
  .detail-panel,
  .sidebar-panel {
    border: 1px solid var(--color-base-300);
    border-radius: 1rem;
    background: var(--color-surface);
    backdrop-filter: blur(6px);
    padding: 1rem;
  }

  .detail-panel,
  .reader-sidebar {
    display: grid;
    gap: 1rem;
    align-content: start;
  }

  .sidebar-title {
    display: block;
    margin-bottom: 0.75rem;
    font-size: var(--font-size-xs);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.55;
  }

  .identity-list {
    display: grid;
    gap: 0.75rem;
  }

  .identity-row {
    display: grid;
    gap: 0.15rem;
  }

  .identity-row dt {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    opacity: 0.5;
  }

  .identity-row dd {
    margin: 0;
    font-size: var(--font-size-sm);
    word-break: break-word;
  }

  .name-pill,
  .lawyer-pill {
    padding: 0.35rem 0.6rem;
    border: 1px solid var(--color-base-300);
    background: var(--color-base-200);
    color: var(--color-primary);
  }

  .lawyer-pill {
    background: rgba(180, 83, 9, 0.1);
    border-color: rgba(180, 83, 9, 0.22);
  }

  .reader-content {
    min-width: 0;
  }

  .reader-text {
    padding: 0.75rem 0;
  }

  .html-content {
    font-size: var(--font-size-sm);
    line-height: 1.8;
    color: var(--color-primary);
  }

  .html-content :global(p) {
    margin: 0 0 1rem;
  }

  .html-content :global(br) {
    line-height: 2;
  }

  .html-content :global(strong),
  .html-content :global(b) {
    font-weight: 700;
  }

  .html-content :global(ul),
  .html-content :global(ol) {
    margin: 0 0 1rem 1.25rem;
  }

  .html-content :global(li) {
    margin-bottom: 0.35rem;
  }

  .html-content :global(a) {
    color: var(--color-accent);
    text-decoration: underline;
  }

  .html-content-reader {
    font-size: 1.08rem;
  }

  .html-content-featured {
    border-top: 1px solid var(--color-base-300);
    padding-top: 1.2rem;
  }

  .reader-paragraph {
    font-size: 1.08rem;
    color: var(--color-primary);
    line-height: 2;
    margin-bottom: 1.5rem;
  }

  @media (max-width: 960px) {
    .story-grid,
    .reader-layout {
      grid-template-columns: 1fr;
    }
  }

  @media (max-width: 720px) {
    .header-actions {
      width: 100%;
      justify-content: flex-start;
    }

    .meta-chip {
      min-width: calc(50% - 0.25rem);
    }
  }

  @media (max-width: 540px) {
    .meta-chip {
      min-width: 100%;
    }

    .reader-body,
    .featured-body,
    .compact-body {
      padding: 1rem;
    }
  }
</style>
