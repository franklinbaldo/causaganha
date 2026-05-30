<script lang="ts">
  import type { DjenPublication } from "../lib/djen";
  import {
    buildEntityTerms,
    buildIdentityRows,
    buildMetaChips,
    buildSearchTerms,
    formatProcessNumber,
    htmlToPreviewText,
    parseText,
    previewText,
    uniqueLawyers,
    uniquePartyNames,
    type HighlightTerm,
    type MetaChip,
  } from "../lib/publicationPresentation";
  import PublicationActions, { type PublicationActionContext } from "./PublicationActions.svelte";
  import PublicationDetailPanel from "./PublicationDetailPanel.svelte";
  import PublicationReader from "./PublicationReader.svelte";
  import PublicationResultItem from "./PublicationResultItem.svelte";

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
    highlightTerms = [],
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
    highlightTerms?: string[];
  } = $props();

  let isReaderMode = $state(false);
  let activeCopied = $state<PublicationActionContext | null>(null);
  let shareTimeoutId: ReturnType<typeof setTimeout> | null = null;

  $effect(() => {
    return () => {
      if (shareTimeoutId) clearTimeout(shareTimeoutId);
    };
  });

  const processNumber = $derived(formatProcessNumber(pub.numero_processo));
  const textParts = $derived(pub.textoRender?.kind === "text" ? parseText(pub.textoRender.content) : []);
  const terms = $derived<HighlightTerm[]>([
    ...buildSearchTerms(highlightTerms),
    ...buildEntityTerms(pub),
  ]);
  const teaser = $derived(
    pub.textoRender?.kind === "text" ? previewText(pub.textoRender.content, compact ? 220 : 420) : null,
  );
  const htmlTeaser = $derived(
    pub.textoRender?.kind === "html" ? htmlToPreviewText(pub.textoRender.content, compact ? 220 : 420) : null,
  );
  const metaChips = $derived<MetaChip[]>(buildMetaChips(pub));
  const identityRows = $derived<MetaChip[]>(buildIdentityRows(pub));
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

  async function handleShare(e: MouseEvent, context: PublicationActionContext) {
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

{#snippet sourceBadge()}
  {#if source}
    <span
      class="badge"
      data-tone={source === "djen" ? "info" : "warning"}
      title={usedFallback ? "Falha ao conectar no DJEN, usando arquivo IA" : ""}
    >
      Fonte: {source === "djen" ? "DJEN" : "Arquivo IA"}
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
  <PublicationResultItem
    {pub}
    {seq}
    {dateStr}
    {source}
    {usedFallback}
    {processNumber}
    {metaChips}
    {parties}
    {lawyers}
    {teaser}
    {htmlTeaser}
    {terms}
    {activeCopied}
    {onExpand}
    onShare={handleShare}
  />
{:else if isReaderMode}
  <PublicationReader
    {pub}
    {seq}
    {dateStr}
    {source}
    {usedFallback}
    {processNumber}
    {metaChips}
    {identityRows}
    {parties}
    {lawyers}
    {textParts}
    {terms}
    {activeCopied}
    onBack={() => (isReaderMode = false)}
    onShare={handleShare}
  />
{:else}
  <article class="publication-card publication-card--expanded" id={`pub-${seq}`}>
    <header class="publication-card__header">
      <div class="publication-card__header-main">
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
      <PublicationActions
        link={pub.link}
        {activeCopied}
        shareContext="main"
        onShare={handleShare}
        showClose={!!onCollapse}
        onClose={onCollapse}
        showReader
        onOpenReader={() => (isReaderMode = true)}
        showNavigation={!!onNavigate}
        {onNavigate}
        {seq}
        {totalSeq}
        ariaLabel="Ações de navegação e leitura"
      />
    </header>

    {#if metaChips.length > 0}
      <div class="meta-chip-row meta-chip-row-spacious">
        {#each metaChips as meta}
          {@render chip(meta)}
        {/each}
      </div>
    {/if}

    <PublicationDetailPanel
      {pub}
      {teaser}
      {textParts}
      {identityRows}
      {parties}
      {lawyers}
    />
  </article>
{/if}
