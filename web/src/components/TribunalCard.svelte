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
