<script lang="ts">
  let {
    tribunal,
    href,
    hasData,
    totalZips,
    latestDate,
  }: {
    tribunal: string;
    href: string;
    hasData: boolean;
    totalZips: number;
    latestDate: string | null;
  } = $props();

  function formatDate(iso: string): string {
    const [y, m, d] = iso.split('-');
    return `${d}/${m}/${y}`;
  }
</script>

<a {href} class="tribunal-link">
  <article class="tribunal-card" class:offline={!hasData}>
    <div class="tribunal-card-header">
      <strong class="small-text">{tribunal}</strong>
      <mark data-tone={hasData ? 'success' : 'error'}>
        {hasData ? "Online" : "Offline"}
      </mark>
    </div>
    <div class="tribunal-card-meta">
      {#if hasData}
        {totalZips.toLocaleString('pt-BR')} publicações
      {:else}
        Sem dados processados
      {/if}
      {#if latestDate}
        <span class="latest-date">Última: {formatDate(latestDate)}</span>
      {/if}
    </div>
  </article>
</a>

<style>
  .tribunal-link {
    display: block;
    height: 100%;
    text-decoration: none;
    color: inherit;
  }

  .tribunal-link:hover .tribunal-card {
    border-color: var(--color-accent);
    box-shadow: var(--shadow-md);
  }

  .tribunal-card {
    height: 100%;
    transition: border-color var(--transition-base), box-shadow var(--transition-base);
  }

  .tribunal-card.offline {
    opacity: 0.6;
  }

  .tribunal-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
  }

  .tribunal-card-meta {
    font-size: var(--font-size-xs);
    opacity: 0.7;
  }

  .latest-date {
    display: block;
    margin-top: 0.25rem;
    opacity: 0.7;
  }
</style>
