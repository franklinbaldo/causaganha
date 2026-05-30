<script lang="ts">
  import type { DjenPublication } from "../lib/djen";
  import {
    highlightText,
    type HighlightTerm,
    type MetaChip,
  } from "../lib/publicationPresentation";
  import PublicationActions, { type PublicationActionContext } from "./PublicationActions.svelte";

  let {
    pub,
    seq,
    dateStr,
    source,
    usedFallback,
    processNumber,
    metaChips = [],
    identityRows = [],
    parties = [],
    lawyers = [],
    textParts = [],
    terms = [],
    activeCopied = null,
    onBack,
    onShare,
  }: {
    pub: DjenPublication;
    seq: number;
    dateStr: string;
    source?: "djen" | "ia";
    usedFallback?: boolean;
    processNumber: string | null;
    metaChips?: MetaChip[];
    identityRows?: MetaChip[];
    parties?: string[];
    lawyers?: string[];
    textParts?: string[];
    terms?: HighlightTerm[];
    activeCopied?: PublicationActionContext | null;
    onBack: () => void;
    onShare: (event: MouseEvent, context: PublicationActionContext) => void;
  } = $props();
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
    <PublicationActions
      link={pub.link}
      {activeCopied}
      shareContext="reader"
      {onShare}
      showBack
      {onBack}
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
        <div class="reader-text highlighted-text">
          {#each textParts as part}
            <p class="reader-paragraph">{@render highlighted(part)}</p>
          {/each}
        </div>
      {/if}
    </div>
  </div>
</article>
