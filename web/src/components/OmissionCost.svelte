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

<style>
  .layout {
    display: grid;
    grid-template-columns: 1fr 2fr;
    gap: 1.5rem;
  }

  @media (max-width: 640px) {
    .layout { grid-template-columns: 1fr; }
  }

  .global-stat {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    text-align: center;
    background: var(--color-base-200);
    border-radius: var(--pico-border-radius);
    padding: 1.5rem;
  }

  .cost {
    font-size: 3rem;
    color: var(--color-error);
  }

  .omission-list {
    list-style: none;
    margin: 0;
    padding: 0;
    max-height: 400px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 0.375rem;
  }

  .omission-item {
    display: grid;
    grid-template-columns: 5rem 1fr auto;
    align-items: center;
    gap: 0.75rem;
    font-size: var(--font-size-sm);
  }

  .omission-name { font-weight: 600; }

  .omission-count {
    font-size: var(--font-size-xs);
    white-space: nowrap;
  }

  progress {
    width: 100%;
    height: 0.5rem;
  }
</style>
