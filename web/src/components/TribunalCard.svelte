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

<article class:offline={!hasData}>
  <header>
    <a {href}>
      <strong class="small-text">{tribunal}</strong>
    </a>
    <mark data-tone={hasData ? 'success' : 'error'}>
      {hasData ? "Online" : "Offline"}
    </mark>
  </header>
  <footer>
    <small>
      {#if hasData}
        {totalZips.toLocaleString('pt-BR')} publicações
      {:else}
        Sem dados processados
      {/if}
      {#if latestDate}
        · <time datetime={latestDate}>Última: {formatDate(latestDate)}</time>
      {/if}
    </small>
  </footer>
</article>
