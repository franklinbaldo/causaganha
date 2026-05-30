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
      /(?=(?:Processo\s*:|Classe\s*:|INTIMA(?:ÇÃO|CAO)|CITA(?:ÇÃO|CAO)|DESPACHO|DECIS(?:ÃO|AO)|SENTEN(?:ÇA|CA)|EDITAL|Designada\s+AUDI(?:ÊNCIA|ENCIA)|DATA\s+E\s+HORA))/gi;
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

  function publicationShareIdentity(): string | null {
    if (pub.hash) return `pub/hash/${encodeURIComponent(pub.hash)}`;
    if (pub.numeroComunicacao != null) {
      return `pub/numeroComunicacao/${encodeURIComponent(String(pub.numeroComunicacao))}`;
    }
    if (pub.id != null) return `pub/id/${encodeURIComponent(String(pub.id))}`;
    return null;
  }

  function publicationShareHash(): string {
    const identity = publicationShareIdentity();

    if (page && dateStr) {
      let dateHash = `${dateStr}/pg/${page}`;
      if (seq) dateHash += `/seq/${seq}`;
      if (identity) dateHash += `/${identity}`;
      return dateHash;
    }

    if (identity) return identity;

    let fallbackHash = dateStr;
    if (seq) fallbackHash += `/seq/${seq}`;
    return fallbackHash;
  }

  async function handleShare(e: MouseEvent, context: "main" | "reader" | "compact") {
    e.preventDefault();
    e.stopPropagation();
    const hash = publicationShareHash();
    const pathAndSearch = `${window.location.pathname}${window.location.search}`;
    const url = `${window.location.origin}${pathAndSearch}#${hash}`;
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
      class="badge"
      data-tone={source === 'djen' ? 'info' : 'warning'}
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
  <article
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
    <header>
      <span class="seq-number">#{seq}</span>
      {#if pub.tipoComunicacao}
        <span class="badge publication-badge">{pub.tipoComunicacao}</span>
      {/if}
      {@render sourceBadge()}
      <small><time>{dateStr}</time></small>
      {#if processNumber}
        <button
          type="button"
          class="process-number process-number-lg process-link"
          onclick={(e: MouseEvent) => { e.stopPropagation(); onExpand?.(); }}
          title="Abrir detalhes da publicação"
        >{processNumber}</button>
      {/if}
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
          <span class="name-pill">{party}</span>
        {/each}
      </div>
    {/if}

    <footer>
      {#if pub.link}
        <a class="outline secondary" href={pub.link} target="_blank" rel="noopener noreferrer" role="button">
          {@render openExternalIcon()}
          Inteiro teor
        </a>
      {/if}
      <button
        type="button"
        class="outline secondary"
        onclick={(e: MouseEvent) => handleShare(e, "compact")}
        title="Copiar link"
      >
        {@render shareIcon()}
        {activeCopied === "compact" ? "Copiado!" : "Link"}
      </button>
    </footer>
  </article>
{:else if isReaderMode}
  <article class="reader-mode" id={`pub-${seq}`}>
    <header>
      <div>
        <span class="seq-number seq-bold">#{seq}</span>
        <span class="badge publication-badge">Modo Leitura</span>
        {@render sourceBadge()}
        <small><time>{dateStr}</time></small>
      </div>
      {#if processNumber}
        <h2 class="process-number process-number-xl">{processNumber}</h2>
      {/if}
      {#if pub.nomeOrgao}
        <p class="orgao-name-reader">{pub.nomeOrgao}</p>
      {/if}
      <div aria-label="Ações de navegação e leitura">
        <button
          type="button"
          class="outline secondary"
          onclick={() => (isReaderMode = false)}
          title="Sair do Modo Leitura"
        >
          Voltar
        </button>
        {#if pub.link}
          <a class="outline secondary" href={pub.link} target="_blank" rel="noopener noreferrer">
            {@render openExternalIcon()}
            Inteiro teor
          </a>
        {/if}
        <button
          type="button"
          class="outline secondary"
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
            <dl>
              {#each identityRows as item}
                <div>
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
                <span class="name-pill">{party}</span>
              {/each}
            {/if}
            {#if lawyers.length > 0}
              {#each lawyers as lawyer}
                <span class="name-pill" data-tone="info">{lawyer}</span>
              {/each}
            {/if}
          </div>
        </div>
      </aside>

      <div class="reader-content">
        {#if pub.textoRender?.kind === "html"}
          <div>
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
  </article>
{:else}
  <article id={`pub-${seq}`}>
    <header>
      <div>
        <span class="seq-number seq-bold">#{seq}</span>
        {#if pub.tipoComunicacao}
          <span class="badge publication-badge">{pub.tipoComunicacao}</span>
        {/if}
        {@render sourceBadge()}
        <small><time>{dateStr}</time></small>
      </div>
      {#if processNumber}
        <strong class="process-number process-number-lg">{processNumber}</strong>
      {/if}
      {#if pub.nomeOrgao}
        <small class="orgao-name-block">{pub.nomeOrgao}</small>
      {/if}
      <div aria-label="Ações de navegação e leitura">
        {#if onCollapse}
          <button
            type="button"
            class="outline secondary"
            onclick={onCollapse}
            title="Fechar detalhes"
          >
            Fechar
          </button>
        {/if}
        <button
          type="button"
          class="outline"
          onclick={() => (isReaderMode = true)}
          title="Abrir Modo Leitura"
        >
          Modo Leitura
        </button>
        {#if pub.link}
          <a class="outline secondary" href={pub.link} target="_blank" rel="noopener noreferrer">
            {@render openExternalIcon()}
            Inteiro teor
          </a>
        {/if}
        <div class="nav-actions" aria-label="Ações de navegação">
          {#if onNavigate}
            <button
              type="button"
              class="outline secondary"
              onclick={() => onNavigate(seq - 1)}
              disabled={seq <= 1}
            >
              Anterior
            </button>
            <button
              type="button"
              class="outline secondary"
              onclick={() => onNavigate(seq + 1)}
              disabled={totalSeq != null && seq >= totalSeq}
            >
              Próxima
            </button>
          {/if}
          <button
            type="button"
            class="outline secondary"
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
      <section>
        {#if teaser}
          <p>{teaser}</p>
        {/if}

        {#if pub.textoRender?.kind === "html"}
          <div>
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
            <dl>
              {#each identityRows as item}
                <div>
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
                <span class="name-pill">{party}</span>
              {/each}
            </div>
          </div>
        {/if}

        {#if lawyers.length > 0}
          <div class="sidebar-panel">
            <strong class="sidebar-title">Advogados</strong>
            <div class="sidebar-tags">
              {#each lawyers as lawyer}
                <span class="name-pill" data-tone="info">{lawyer}</span>
              {/each}
            </div>
          </div>
        {/if}
      </aside>
    </div>
  </article>
{/if}
