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

      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Tribunal</th>
              <th>Dias Omitidos</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {#each rankedTribunals() as {tribunal, count}, i}
              <tr>
                <td><small>{i + 1}</small></td>
                <td>{tribunal}</td>
                <td><kbd>{count}</kbd></td>
                <td>
                  <progress
                    value={count}
                    max={rankedTribunals()[0]?.count || 1}
                    aria-label="{tribunal}: {count} dias omitidos"
                  ></progress>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    </div>
  {/if}
</article>

<style>
  header {
    background: none;
    padding: 0;
    margin-bottom: 1rem;
  }

  h2 { margin: 0; }

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

  .table-wrap {
    max-height: 400px;
    overflow-y: auto;
  }

  progress {
    width: 100%;
    height: 0.5rem;
  }
</style>
