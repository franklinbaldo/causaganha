<script lang="ts">
  import type { DjenPublication } from "../lib/djen";
  import { highlightText, type HighlightTerm, type MetaChip } from "../lib/publicationPresentation";
  import PublicationActions, { type PublicationActionContext } from "./PublicationActions.svelte";

  let {
    pub,
    seq,
    dateStr,
    source,
    usedFallback,
    processNumber,
    metaChips = [],
    parties = [],
    lawyers = [],
    teaser,
    htmlTeaser,
    terms = [],
    activeCopied = null,
    onExpand,
    onShare,
  }: {
    pub: DjenPublication;
    seq: number;
    dateStr: string;
    source?: "djen" | "ia";
    usedFallback?: boolean;
    processNumber: string | null;
    metaChips?: MetaChip[];
    parties?: string[];
    lawyers?: string[];
    teaser: string | null;
    htmlTeaser: string | null;
    terms?: HighlightTerm[];
    activeCopied?: PublicationActionContext | null;
    onExpand?: () => void;
    onShare: (event: MouseEvent, context: PublicationActionContext) => void;
  } = $props();

  const preview = $derived(pub.textoRender?.kind === "html" ? htmlTeaser : teaser);
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

{#snippet highlighted(value: string)}
  {#each highlightText(value, terms) as segment}
    {#if segment.type}
      <mark class={`entity-${segment.type}`}>{segment.token}</mark>
    {:else}
      {segment.token}
    {/if}
  {/each}
{/snippet}

<article class:expandable={!!onExpand} id={`pub-${seq}`}>
  <header>
    <span class="seq-number">#{seq}</span>
    {#if pub.tipoComunicacao}
      <span class="badge publication-badge">{pub.tipoComunicacao}</span>
    {/if}
    {@render sourceBadge()}
    <small><time>{dateStr}</time></small>
    {#if processNumber}
      {#if onExpand}
        <button
          type="button"
          class="process-number process-number-lg process-link"
          onclick={onExpand}
          title="Abrir detalhes da publicação"
        >{processNumber}</button>
      {:else}
        <strong class="process-number process-number-lg">{processNumber}</strong>
      {/if}
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

  {#if preview}
    <p class="text-preview highlighted-text">{@render highlighted(preview)}</p>
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
    {#if onExpand}
      <button type="button" class="outline" onclick={onExpand} title="Abrir detalhes da publicação">
        Abrir detalhes
      </button>
    {/if}
    <PublicationActions
      link={pub.link}
      {activeCopied}
      shareContext="compact"
      shareLabel="Link"
      {onShare}
      ariaLabel="Ações do resultado compacto"
    />
  </footer>
</article>
