<script lang="ts">
  import type { DjenPublication } from "../lib/djen";
  import { type MetaChip } from "../lib/publicationPresentation";

  let {
    pub,
    teaser,
    textParts = [],
    identityRows = [],
    parties = [],
    lawyers = [],
  }: {
    pub: DjenPublication;
    teaser: string | null;
    textParts?: string[];
    identityRows?: MetaChip[];
    parties?: string[];
    lawyers?: string[];
  } = $props();
</script>

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
