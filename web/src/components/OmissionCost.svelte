<script lang="ts">
  type OmissionStats = {
    global_omission_cost: number;
    tribunals: Record<string, number>;
    generated_at: string;
  };

  let { omissionStats }: { omissionStats: OmissionStats | null } = $props();

  let globalOmissionCost = $derived(omissionStats?.global_omission_cost || 0);

  let rankedTribunals = $derived(() => {
    if (!omissionStats?.tribunals) return [];
    return Object.entries(omissionStats.tribunals)
      .map(([tribunal, count]) => ({ tribunal, count }))
      .sort((a, b) => b.count - a.count);
  });
</script>

<article>
  <header>
    <h2>Omission Cost</h2>
  </header>

  {#if !omissionStats}
    <p aria-busy="true">Carregando dados...</p>
  {:else}
    <div class="layout">
      <div class="global-stat">
        <small>Global Omission Cost</small>
        <strong class="cost">{globalOmissionCost}</strong>
        <small>Dias úteis perdidos (sem .zip ou .absent)</small>
      </div>

      <ol class="omission-list">
        {#each rankedTribunals() as {tribunal, count}}
          <li class="omission-item">
            <span class="omission-name">{tribunal}</span>
            <progress value={count} max={rankedTribunals()[0]?.count || 1} aria-label="{tribunal}: {count} dias omitidos"></progress>
            <kbd class="omission-count">{count}</kbd>
          </li>
        {/each}
      </ol>
    </div>
  {/if}
</article>
